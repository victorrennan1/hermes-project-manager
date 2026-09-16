# The Competitor Dashboard — full setup guide

This is the system from the reel: every morning it can rebuild a dashboard of your competitors' latest reels — who's posting, which hooks are pulling views, the full script of every reel broken into Hook / Beats / CTA — so you review your niche in about three minutes instead of scrolling for hours.

You're getting the whole thing:

| # | File | What it is |
|---|---|---|
| 1 | `setup.py` | The setup screen — enter your niche and competitors in a browser form |
| 1b | `competitor-accounts.md` | Your competitor list — what the setup screen writes (editable by hand too) |
| 2 | `scrape.py` | The scraper — pulls competitor reels + transcribes them (the only code you run) |
| 3 | `ANALYZE.md` | The analysis playbook Claude follows to score + break down every reel |
| 4 | `DASHBOARD-SPEC.md` | The spec Claude follows to build your dashboard.html |

**You don't need to be able to code.** The fastest path is to hand this whole pack to Claude and let it do the setup.

---

## The 5-minute version (recommended)

1. Install [Claude Code](https://claude.com/claude-code) if you don't have it.
2. Make a folder (e.g. `competitor-dashboard/`) and save all five files into it.
3. Open Claude Code in that folder and say:

> Read README.md and set this competitor dashboard up for me. My niche is **[what you make content about, and for whom]**. My competitors are **[3–7 Instagram handles]**. Walk me through getting the two API keys, then do the rest yourself.

Claude will take it from there — including editing the niche line in `ANALYZE.md` and filling `competitor-accounts.md` for you.

---

## What it costs to run

- **Apify** (does the Instagram scraping) — this is the main cost, and you pay it per run based on `--limit` × accounts, whether or not the reels turn out to be new. A few dollars a month at 3 reels per account, a handful of accounts, run a few times a week. New accounts get free monthly credit, which covers a lot of it. Check yours any time with `python3 scrape.py --balance`.
- **ElevenLabs Scribe** (transcription) — pennies per batch. Free tier usually covers it.
- **The analysis is free** — Claude does the scoring, breakdowns, and dashboard in your normal session. No OpenAI key, no extra subscription.

Realistic total: **about $5/month.**

## The two keys you need

1. **Apify** — sign up at [apify.com](https://apify.com) → Settings → Integrations → copy your API token.
2. **ElevenLabs** — sign up at [elevenlabs.io](https://elevenlabs.io) → your profile → API keys → create one.

Then set them in your terminal (Claude can put these in your shell profile so it's permanent):

```bash
export APIFY_TOKEN="your-apify-token"
export ELEVENLABS_API_KEY="your-elevenlabs-key"
```

## Manual setup (if you'd rather drive)

Needs Python 3.10+ — `pip install -r requirements.txt`.

1. Run the setup screen and fill in the form (niche, competitors, and optionally your two keys — they go in a gitignored `.env` so you stop re-exporting them):

```bash
python3 setup.py
```

It opens `http://127.0.0.1:8765`, loopback only, and writes `ANALYZE.md` + `competitor-accounts.md` for you. Ctrl-C when you're done. Prefer editing markdown by hand? Fill in `competitor-accounts.md` (one row per competitor, `Active = yes` to track) and replace the **YOUR NICHE** line at the top of `ANALYZE.md` — the setup screen is a convenience, not a requirement.

2. Run the scraper:

```bash
python3 scrape.py               # 3 latest reels per active account
python3 scrape.py --limit 5     # or 5 per account
python3 scrape.py --balance     # check your Apify spend/credit first
```

3. Tell Claude: **"Process the latest batch in staging/ following ANALYZE.md."** It scores every reel for relevance to your niche, splits the transcript into Hook / Beats / CTA, and writes one note per keeper into `notes/`.
4. Tell Claude: **"Build the dashboard following DASHBOARD-SPEC.md."** You get a `dashboard.html` — open it in your browser.
5. Repeat whenever you want fresh data: scrape → "process the batch" → "rebuild the dashboard". The scraper remembers what it's already seen, so a reel you've already staged is never downloaded or transcribed twice. Apify still charges for the listing itself each run — keep `--limit` low and that stays cheap.

## The weekly rhythm

Run it once or twice a week. Open the dashboard, read the top hooks and the taxonomy (which hook styles keep winning in your niche), pick your angles. That's the whole point: **you stop watching reels and start watching patterns.**

Want it to actually run every morning, hands-off? Ask Claude to schedule `scrape.py` for you (launchd/cron on Mac, Task Scheduler on Windows). Out of the box it's run-when-you-want — which is honestly enough.

## Fair-use notes (read this once)

- This is **research signal**, not a content-theft kit. You're studying what works — hooks, structures, topics — not republishing anyone's reels. Don't repost the videos or transcripts.
- Use your own Apify account and keep the volume reasonable (the defaults are). Scraping public Instagram data sits in a gray area of Instagram's terms — the same gray area every analytics tool lives in — but it's your account and your call.
- The downloaded videos in `staging/videos/` are working files for transcription. Delete them after a batch is processed; the transcripts stay in your notes.

## Troubleshooting

- **"APIFY_TOKEN not set"** — the export lines above aren't in your current terminal. Re-run them (or ask Claude to add them to your shell profile).
- **Scrape returns 0 items** — check the handles in `competitor-accounts.md` are exact Instagram usernames (no `@`), and marked `Active = yes`.
- **A transcript comes back empty** — some reels are music-only. They still stage; Claude scores them from the caption.
- Anything else: paste the error into Claude. It has all five files — it can fix its own plumbing.
