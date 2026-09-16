#!/usr/bin/env python3
"""Competitor dashboard — the setup screen.

Fills in the two things the pipeline can't guess: your niche (ANALYZE.md) and
your competitor list (competitor-accounts.md). Optionally stores your API keys
in a gitignored .env so you don't re-export them every terminal.

    python3 setup.py            # opens http://127.0.0.1:8765 in your browser
    python3 setup.py --port 9000
    python3 setup.py --no-open  # just serve, don't launch a browser

Stdlib only — the scraper's one dependency stays the scraper's.
"""
from __future__ import annotations
import argparse, http.server, json, re, sys, threading, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCOUNTS_MD = ROOT / "competitor-accounts.md"
ANALYZE_MD = ROOT / "ANALYZE.md"
ENV_FILE = ROOT / ".env"

NICHE_RE = re.compile(r"^> \*\*YOUR NICHE:\*\*.*$", re.MULTILINE)
NICHE_PLACEHOLDER = "I make content about **[topic]** for **[audience]**."

ACCOUNTS_HEADER = """# Competitor accounts

The scraper reads every row where **Active = yes**. Exact Instagram usernames, no `@` needed. Start with 3–7 accounts — the ones whose audience you actually want.

Good picks: accounts your size or 1–2 tiers above you, posting reels consistently in your niche. Skip celebrities — their numbers don't tell you anything you can use.

"""

ACCOUNTS_FOOTER = """
**Maintain it:** when an account goes quiet or drifts off-niche, flip it to `no` (don't delete the row — the history explains itself later). Add new finds as you spot them; the dashboard's "reach by account" view will tell you quickly who's worth keeping.
"""


# ---------------------------------------------------------------- read state

def read_niche() -> str:
    """The niche line minus its markdown wrapper, or '' while it's the template."""
    if not ANALYZE_MD.exists():
        return ""
    m = NICHE_RE.search(ANALYZE_MD.read_text(encoding="utf-8"))
    if not m:
        return ""
    line = m.group(0)[len("> **YOUR NICHE:**"):].strip()
    return "" if "[topic]" in line else re.sub(r"\*\*", "", line)


def read_accounts() -> list[dict]:
    """Parse the table back out so the form opens on what's already there."""
    if not ACCOUNTS_MD.exists():
        return []
    rows = []
    for line in ACCOUNTS_MD.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        user = cells[0].lstrip("@")
        if user.lower() in ("username", "") or "---" in user:
            continue
        rows.append({"username": user, "why": cells[1], "size": cells[2],
                     "active": cells[3].lower() == "yes"})
    return rows


def read_env() -> dict:
    """Report only whether each key is set — never ship the value to the page."""
    have = {"APIFY_TOKEN": False, "ELEVENLABS_API_KEY": False}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            name, _, val = line.partition("=")
            if name.strip() in have and val.strip().strip('"'):
                have[name.strip()] = True
    return have


# --------------------------------------------------------------- write state

def write_niche(niche: str):
    text = ANALYZE_MD.read_text(encoding="utf-8")
    body = niche.strip() or NICHE_PLACEHOLDER
    if not NICHE_RE.search(text):
        raise ValueError("couldn't find the YOUR NICHE line in ANALYZE.md")
    ANALYZE_MD.write_text(NICHE_RE.sub(f"> **YOUR NICHE:** {body}", text, count=1),
                          encoding="utf-8")


def write_accounts(rows: list[dict]):
    out = [ACCOUNTS_HEADER,
           "| Username | Niche / why tracked | Size (rough) | Active |",
           "| --- | --- | --- | --- |"]
    for r in rows:
        # Pipes in free text would split the row when the scraper re-parses it.
        why = r.get("why", "").replace("|", "/") or "—"
        size = r.get("size", "").replace("|", "/") or "—"
        out.append(f"| {r['username']} | {why} | {size} | {'yes' if r.get('active') else 'no'} |")
    ACCOUNTS_MD.write_text("\n".join(out) + "\n" + ACCOUNTS_FOOTER, encoding="utf-8")


def write_env(keys: dict):
    """Merge into .env, keeping any key the form left blank. Gitignored."""
    current = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            name, sep, val = line.partition("=")
            if sep:
                current[name.strip()] = val.strip()
    for name, val in keys.items():
        if val.strip():
            current[name] = f'"{val.strip()}"'
    if current:
        ENV_FILE.write_text("".join(f"{k}={v}\n" for k, v in current.items()), encoding="utf-8")


def clean_handle(raw: str) -> str:
    """Accept a handle, an @handle, or a pasted profile URL."""
    raw = raw.strip()
    m = re.search(r"instagram\.com/([A-Za-z0-9._]+)", raw)
    if m:
        raw = m.group(1)
    return raw.lstrip("@").strip("/ ").strip()


# ---------------------------------------------------------------------- page

PAGE = r"""<!doctype html>
<meta charset="utf-8"><title>Competitor dashboard — setup</title>
<style>
  :root { --accent:#4f46e5; --ink:#18181b; --muted:#71717a; --line:#e4e4e7; --bg:#fafafa; }
  * { box-sizing:border-box; }
  body { margin:0; padding:48px 24px 96px; background:var(--bg); color:var(--ink);
         font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  main { max-width:780px; margin:0 auto; }
  h1 { font-size:26px; margin:0 0 6px; letter-spacing:-.02em; }
  .sub { color:var(--muted); margin:0 0 36px; }
  section { background:#fff; border:1px solid var(--line); border-radius:12px;
            padding:24px; margin-bottom:20px; }
  h2 { font-size:14px; text-transform:uppercase; letter-spacing:.06em;
       color:var(--muted); margin:0 0 4px; }
  .hint { color:var(--muted); font-size:13px; margin:0 0 16px; }
  label { display:block; font-size:13px; color:var(--muted); margin-bottom:5px; }
  input[type=text], input[type=password] { width:100%; padding:9px 11px; font:inherit;
    border:1px solid var(--line); border-radius:7px; background:#fff; color:var(--ink); }
  input:focus { outline:2px solid var(--accent); outline-offset:-1px; border-color:transparent; }
  table { width:100%; border-collapse:collapse; }
  th { text-align:left; font-size:12px; color:var(--muted); font-weight:500; padding:0 8px 8px 0; }
  td { padding:0 8px 8px 0; vertical-align:middle; }
  td:last-child, th:last-child { width:34px; padding-right:0; }
  .rm { border:0; background:none; color:var(--muted); cursor:pointer; font-size:19px;
        line-height:1; padding:4px 6px; border-radius:5px; }
  .rm:hover { background:#fee2e2; color:#b91c1c; }
  button.act { font:inherit; font-weight:500; cursor:pointer; border-radius:8px; padding:9px 15px; }
  .ghost { background:#fff; border:1px solid var(--line); color:var(--ink); }
  .ghost:hover { border-color:var(--accent); color:var(--accent); }
  .primary { background:var(--accent); border:1px solid var(--accent); color:#fff; padding:11px 22px; }
  .primary:disabled { opacity:.5; cursor:default; }
  .bar { position:fixed; left:0; right:0; bottom:0; background:#fff; border-top:1px solid var(--line);
         padding:14px 24px; display:flex; justify-content:center; gap:16px; align-items:center; }
  .bar .inner { width:780px; max-width:100%; display:flex; align-items:center; gap:16px; }
  #msg { font-size:13px; }
  .ok { color:#15803d; } .err { color:#b91c1c; }
  .chk { display:flex; align-items:center; gap:7px; font-size:13px; color:var(--muted); }
  .set { color:#15803d; font-size:12px; }
  code { background:#f4f4f5; padding:1px 5px; border-radius:4px; font-size:13px; }
</style>
<main>
  <h1>Competitor dashboard — setup</h1>
  <p class="sub">Fills in <code>ANALYZE.md</code> and <code>competitor-accounts.md</code>. Everything stays on this machine.</p>

  <section>
    <h2>Your niche</h2>
    <p class="hint">One sentence. Every reel gets scored 1–10 against this line, and only 7+ becomes a note — so be specific. Vague niche, noisy dashboard.</p>
    <input type="text" id="niche" placeholder="I make content about strength training for busy professionals over 30.">
  </section>

  <section>
    <h2>Competitors</h2>
    <p class="hint">3–7 accounts, your size or 1–2 tiers above. Handle, @handle or a pasted profile URL all work. Untick Active to park a row without losing it.</p>
    <table><thead><tr><th>Username</th><th>Why tracked</th><th>Size</th><th>Active</th><th></th></tr></thead>
      <tbody id="rows"></tbody></table>
    <button class="act ghost" onclick="addRow()" style="margin-top:12px">+ Add account</button>
  </section>

  <section>
    <h2>API keys <span class="hint" style="text-transform:none;letter-spacing:0">— optional</span></h2>
    <p class="hint">Saved to a gitignored <code>.env</code> that the scraper reads, so you stop re-exporting them. Leave blank to keep using environment variables.</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div><label>APIFY_TOKEN <span id="s_apify"></span></label><input type="password" id="apify" placeholder="apify_api_…"></div>
      <div><label>ELEVENLABS_API_KEY <span id="s_el"></span></label><input type="password" id="el" placeholder="sk_…"></div>
    </div>
  </section>
</main>

<div class="bar"><div class="inner">
  <button class="act primary" id="save" onclick="save()">Save setup</button>
  <span id="msg"></span>
</div></div>

<script>
const $ = id => document.getElementById(id);
let state = {accounts: []};

function addRow(a) {
  a = a || {username:"", why:"", size:"", active:true};
  const tb = $("rows"), tr = document.createElement("tr");
  tr.innerHTML = `<td><input type="text" class="u" placeholder="handle"></td>
    <td><input type="text" class="w" placeholder="direct competitor"></td>
    <td><input type="text" class="s" placeholder="10k"></td>
    <td><span class="chk"><input type="checkbox" class="a"></span></td>
    <td><button class="rm" title="Remove">&times;</button></td>`;
  tr.querySelector(".u").value = a.username;
  tr.querySelector(".w").value = a.why === "—" ? "" : a.why;
  tr.querySelector(".s").value = a.size === "—" ? "" : a.size;
  tr.querySelector(".a").checked = !!a.active;
  tr.querySelector(".rm").onclick = () => tr.remove();
  tb.appendChild(tr);
}

function collect() {
  return [...$("rows").children].map(tr => ({
    username: tr.querySelector(".u").value,
    why:      tr.querySelector(".w").value,
    size:     tr.querySelector(".s").value,
    active:   tr.querySelector(".a").checked,
  })).filter(r => r.username.trim());
}

async function save() {
  const accounts = collect();
  const msg = $("msg");
  if (!$("niche").value.trim()) { msg.className = "err"; msg.textContent = "Set your niche first — the scoring depends on it."; return; }
  if (!accounts.some(a => a.active)) { msg.className = "err"; msg.textContent = "Tick Active on at least one account, or the scraper has nothing to fetch."; return; }
  $("save").disabled = true; msg.className = ""; msg.textContent = "Saving…";
  try {
    const r = await fetch("/save", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({niche:$("niche").value, accounts,
        keys:{APIFY_TOKEN:$("apify").value, ELEVENLABS_API_KEY:$("el").value}})});
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || "save failed");
    msg.className = "ok"; msg.textContent = d.message;
    $("apify").value = ""; $("el").value = "";
    load(true);
  } catch (e) { msg.className = "err"; msg.textContent = String(e.message || e); }
  $("save").disabled = false;
}

async function load(keysOnly) {
  const d = await (await fetch("/state")).json();
  $("s_apify").innerHTML = d.keys.APIFY_TOKEN ? '<span class="set">· saved</span>' : "";
  $("s_el").innerHTML = d.keys.ELEVENLABS_API_KEY ? '<span class="set">· saved</span>' : "";
  if (keysOnly) return;
  $("niche").value = d.niche;
  $("rows").innerHTML = "";
  (d.accounts.length ? d.accounts : [0,0,0]).forEach(a => addRow(a || undefined));
}
load();
</script>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            return self._send(200, PAGE, "text/html")
        if self.path == "/state":
            return self._send(200, json.dumps({
                "niche": read_niche(), "accounts": read_accounts(), "keys": read_env()}))
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/save":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            rows = []
            for r in data.get("accounts", []):
                handle = clean_handle(r.get("username", ""))
                if handle:
                    rows.append({**r, "username": handle})
            if not any(r.get("active") for r in rows):
                raise ValueError("no active accounts — the scraper would have nothing to fetch")
            write_niche(data.get("niche", ""))
            write_accounts(rows)
            write_env(data.get("keys", {}))
            active = sum(1 for r in rows if r.get("active"))
            print(f"  saved — niche set, {len(rows)} account(s), {active} active")
            self._send(200, json.dumps({"message":
                f"Saved · {active} active account(s). Next: python3 scrape.py"}))
        except Exception as e:
            self._send(400, json.dumps({"error": str(e)}))

    def log_message(self, *a):  # keep the terminal to our own messages
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    for f in (ACCOUNTS_MD, ANALYZE_MD):
        if not f.exists():
            sys.exit(f"{f.name} not found — run this from the folder holding the kit")

    # Loopback only: this form writes files and takes API keys. It is not
    # something to expose on the network.
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"setup screen: {url}   (ctrl-c when you're done)")
    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nclosed.")


if __name__ == "__main__":
    main()
