#!/usr/bin/env python3
"""Competitor dashboard — the scraper (standalone starter).

Mechanical stages only: scrape -> dedup -> download -> transcribe -> stage.
The thinking (scoring, breakdowns, dashboard) is done by Claude in-session —
see ANALYZE.md and DASHBOARD-SPEC.md.

Setup:
    pip install requests
    export APIFY_TOKEN="..."          # apify.com -> Settings -> Integrations
    export ELEVENLABS_API_KEY="..."   # elevenlabs.io -> profile -> API keys

Run:
    python3 scrape.py                 # 3 latest reels per active account
    python3 scrape.py --limit 5       # 5 per account
    python3 scrape.py --accounts some_handle another_handle
    python3 scrape.py --no-transcribe # stage metadata only (no ElevenLabs)
    python3 scrape.py --balance       # print Apify usage/credit and exit
"""
from __future__ import annotations
import argparse, datetime, json, os, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCOUNTS_MD = ROOT / "competitor-accounts.md"
NOTES_DIR = ROOT / "notes"          # Claude writes one note per keeper here
LEDGER = ROOT / "ledger.json"       # dedup memory — you only pay for NEW reels
STAGING = ROOT / "staging"
VIDEOS = STAGING / "videos"
APIFY_ACTOR = "xMc5Ga1oCONPmWJIa"   # Apify's Instagram Reel Scraper actor
APIFY_API = "https://api.apify.com/v2"

try:
    import requests
except ImportError:
    sys.exit("The 'requests' package is missing — run: pip install requests")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def load_dotenv():
    """Read the gitignored .env that setup.py writes. A real environment
    variable always wins, so an export still overrides the saved key."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, val = line.partition("=")
        if sep and not os.environ.get(name.strip()):
            os.environ[name.strip()] = val.strip().strip('"').strip("'")


def env_key(name: str, hint: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        sys.exit(f"{name} not set — {hint} (or run: python3 setup.py)")
    return val


def with_retry(fn, *, what: str, attempts: int = 3, base_delay: float = 2.0):
    """Retry transient failures with exponential backoff so one network blip
    doesn't kill the run. Re-raises the last error after the final attempt."""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt == attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            print(f"  {what} failed (attempt {attempt}/{attempts}): {e} — retrying in {delay:.0f}s")
            time.sleep(delay)
    raise last_exc


def write_json(path: Path, data, **dump_kw):
    """Atomic write — a crash mid-write can't corrupt the ledger/batch.

    Always UTF-8: we dump with ensure_ascii=False, and write_text() would
    otherwise use the platform's locale encoding (cp1252 on Windows), which
    mangles any non-English transcript and makes the file unreadable later.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, **dump_kw), encoding="utf-8")
    tmp.replace(path)


def active_accounts() -> list[str]:
    if not ACCOUNTS_MD.exists():
        sys.exit(f"{ACCOUNTS_MD.name} not found — fill in the template first")
    users = []
    for line in ACCOUNTS_MD.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        user, active = cells[0].lstrip("@"), cells[-1].lower()
        if user.lower() in ("username", "") or "---" in user:
            continue
        if active == "yes":
            users.append(user)
    if not users:
        sys.exit("No rows with Active = yes in competitor-accounts.md")
    return users


def shortcode_from_url(url: str) -> str:
    m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url or "")
    return m.group(1) if m else (re.sub(r"[^A-Za-z0-9_-]", "", (url or ""))[-11:] or "unknown")


def load_ledger() -> dict:
    """Always returns all three buckets — the ledger is hand-edited by Claude
    during analysis, so a missing key must not crash the next scrape."""
    ledger = {"processed": [], "low_score": [], "scraped": []}
    if LEDGER.exists():
        stored = json.loads(LEDGER.read_text(encoding="utf-8"))
        for key in ledger:
            if isinstance(stored.get(key), list):
                ledger[key] = stored[key]
    return ledger


def existing_shortcodes() -> set[str]:
    codes = set()
    if NOTES_DIR.exists():
        for f in NOTES_DIR.rglob("SCRAPED-*.md"):
            m = re.search(r"source_url:\s*(\S+)", f.read_text(encoding="utf-8"))
            if m:
                codes.add(shortcode_from_url(m.group(1)))
    return codes


def run_apify(token: str, usernames: list[str], per_account: int, max_wait: int = 900) -> list[dict]:
    """Start the actor, poll until it finishes, then read its dataset.

    Deliberately NOT the run-sync endpoint: a client-side timeout there leaves
    the run going on Apify's side, and retrying starts a SECOND paid run — you
    get billed twice for the same batch. Starting the run once and polling means
    a network blip only costs another poll. The start call is the one thing we
    never retry, for the same reason.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    body = {"resultsLimit": per_account, "username": usernames}

    r = requests.post(f"{APIFY_API}/acts/{APIFY_ACTOR}/runs", json=body, headers=headers, timeout=60)
    r.raise_for_status()
    run = r.json()["data"]
    run_id = run["id"]
    print(f"  run {run_id} started — https://console.apify.com/actors/runs/{run_id}")

    deadline = time.time() + max_wait
    while True:
        def _status():
            s = requests.get(f"{APIFY_API}/actor-runs/{run_id}", headers=headers, timeout=60)
            s.raise_for_status()
            return s.json()["data"]
        run = with_retry(_status, what="Apify status")
        status = run["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            sys.exit(f"Apify run ended as {status} — see the run log linked above")
        if time.time() > deadline:
            sys.exit(f"Apify run still {status} after {max_wait}s — it may still finish; "
                     f"check the run log above rather than re-running (that would bill you again)")
        time.sleep(5)

    def _items():
        s = requests.get(f"{APIFY_API}/datasets/{run['defaultDatasetId']}/items",
                         params={"clean": "true", "format": "json"}, headers=headers, timeout=120)
        s.raise_for_status()
        return s.json()
    return with_retry(_items, what="Apify dataset")


def print_balance(token: str):
    def _call():
        r = requests.get("https://api.apify.com/v2/users/me/limits",
                         headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        return r.json().get("data", {})
    d = with_retry(_call, what="Apify usage")
    cur, lim = d.get("current", {}), d.get("limits", {})
    used, cap = cur.get("monthlyUsageUsd"), lim.get("maxMonthlyUsageUsd")
    print("Apify usage this cycle:")
    if used is not None and cap is not None:
        print(f"  ${used:.2f} / ${cap:.2f} used   (~${cap - used:.2f} left)")
    print(f"  cycle resets: {d.get('monthlyUsageCycle', {}).get('endAt', '?')}")


def field(item: dict, *names, default=None):
    for n in names:
        if item.get(n) not in (None, ""):
            return item[n]
    return default


def download_video(video_url: str, dest: Path, attempts: int = 3, base_delay: float = 1.0) -> bool:
    """Download one reel with retry. Returns False (never raises) so one bad
    file skips instead of aborting the whole batch."""
    for attempt in range(1, attempts + 1):
        try:
            with requests.get(video_url, headers={"User-Agent": UA}, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        fh.write(chunk)
            if dest.stat().st_size > 1000:
                return True
            raise ValueError(f"file too small ({dest.stat().st_size} bytes)")
        except Exception as e:
            if attempt == attempts:
                print(f"    download failed after {attempts} attempts: {e}")
                return False
            delay = base_delay * (2 ** (attempt - 1))
            print(f"    download attempt {attempt}/{attempts} failed: {e} — retrying in {delay:.0f}s")
            time.sleep(delay)
    return False


def transcribe(video_path: Path, api_key: str) -> str:
    """ElevenLabs Scribe speech-to-text on the downloaded reel."""
    def _call():
        with open(video_path, "rb") as fh:
            r = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": api_key},
                data={"model_id": "scribe_v1"},
                files={"file": (video_path.name, fh, "video/mp4")},
                timeout=300,
            )
        r.raise_for_status()
        return r.json()
    try:
        data = with_retry(_call, what="transcribe")
    except Exception as e:
        print(f"    transcribe failed: {e}")
        return ""
    if isinstance(data.get("text"), str) and data["text"].strip():
        return data["text"].strip()
    words = data.get("words") or []
    return " ".join(w.get("text", "") for w in words if w.get("type", "word") == "word").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=3, help="reels per account")
    ap.add_argument("--accounts", nargs="*", help="override the account list")
    ap.add_argument("--no-transcribe", action="store_true")
    ap.add_argument("--cap", type=int, default=50, help="max new reels per run")
    ap.add_argument("--balance", action="store_true", help="print Apify usage and exit")
    args = ap.parse_args()

    load_dotenv()
    token = env_key("APIFY_TOKEN", "get it at apify.com -> Settings -> Integrations")
    if args.balance:
        print_balance(token)
        return
    el_key = "" if args.no_transcribe else env_key("ELEVENLABS_API_KEY", "get it at elevenlabs.io -> profile -> API keys")

    STAGING.mkdir(exist_ok=True)
    VIDEOS.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(exist_ok=True)
    accounts = args.accounts or active_accounts()
    print(f"accounts ({len(accounts)}): {', '.join(accounts)}  ·  {args.limit}/account")

    ledger = load_ledger()
    seen = set(ledger["processed"]) | set(ledger["low_score"]) | set(ledger["scraped"]) | existing_shortcodes()
    print(f"dedup set: {len(seen)} known shortcodes")

    print("calling Apify…")
    items = run_apify(token, accounts, args.limit)
    print(f"  Apify returned {len(items)} items")

    batch, new = [], 0
    failures: list[tuple[str, str, str]] = []
    for it in items:
        if new >= args.cap:
            break
        url = field(it, "url", "postUrl", default="")
        # No displayUrl fallback: that's the thumbnail. It would download as a
        # JPEG named .mp4, pass the size check, and burn a Scribe call for nothing.
        video_url = field(it, "videoUrl", "video_url")
        code = shortcode_from_url(url)
        if not video_url or code in seen:
            continue
        user = field(it, "ownerUsername", "username", "ownerUserName", default="unknown")
        print(f"  [{user}] {code}")
        try:
            vpath = VIDEOS / f"{code}.mp4"
            if not download_video(video_url, vpath):
                failures.append((user, code, "download failed"))
                continue
            transcript = "" if args.no_transcribe else transcribe(vpath, el_key)
            if not args.no_transcribe and not transcript:
                print("    (no transcript — staging anyway)")
            batch.append({
                "shortcode": code,
                "username": user,
                "url": url,
                "views": field(it, "videoViewCount", "videoPlayCount", "playCount", default=0),
                "likes": field(it, "likesCount", "likeCount", default=0),
                "comments": field(it, "commentsCount", "commentCount", default=0),
                "caption": field(it, "caption", "text", default=""),
                "transcript": transcript,
                "status": "needs-analysis",
            })
            seen.add(code)
            new += 1
        except Exception as e:
            print(f"    ERROR processing {code}: {e} — skipping")
            failures.append((user, code, f"error: {e}"))
            continue

    date = datetime.date.today().isoformat()
    batch_path = STAGING / f"batch-{date}.json"
    write_json(batch_path, batch, indent=2, ensure_ascii=False)
    ledger["scraped"] = sorted(set(ledger["scraped"]) | {b["shortcode"] for b in batch})
    write_json(LEDGER, ledger, indent=2)

    print(f"\nstaged {len(batch)} new reels -> {batch_path.name}")
    if failures:
        print(f"! {len(failures)} item(s) skipped (batch kept going):")
        for user, code, why in failures:
            print(f"    [{user}] {code} — {why}")
    print('next: tell Claude — "process the latest batch in staging/ following ANALYZE.md"')


if __name__ == "__main__":
    main()
