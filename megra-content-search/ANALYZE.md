# Analysis playbook — what Claude does with a staged batch

After `scrape.py` stages `staging/batch-{date}.json`, Claude processes every item **in your session** — this is the "AI stage" of the pipeline and it costs nothing extra. Say: **"Process the latest batch in staging/ following ANALYZE.md."**

## 0. Your niche (EDIT THIS LINE — the whole system keys off it)

> **YOUR NICHE:** Eu faço conteúdo sobre startup, inovação, empreendedorismo e inteligência artificial
> *(Example: "I make content about strength training for busy professionals over 30.")*

## 1. Score + break down (per reel)

Filter the reel transcripts for relevance to YOUR NICHE, scoring each **1–10**:

- **10**: directly on-niche — the exact topics you post about
- **7–9**: adjacent — same audience, neighbouring topic
- **4–6**: general/hype content with a loose angle on your niche
- **1–3**: off-topic (lifestyle, unrelated verticals)

Extract per reel:

- `topic`: 4–8 word summary of what the reel teaches
- `tools`: array of named products / services mentioned (if any)
- `hookStyle`: one of `["problem-promise","contrarian-claim","list-tease","demo-first","story-frame","data-shock","identity-call","other"]`
- `verdict`: `true` if score >= 7 AND there's a teachable insight, else `false`
- `reasoning`: one sentence
- `sections`: split the transcript into structural beats — array of `{label, text, note}`:
  - `label`: `Hook` (the first 1–2 lines / attention grab), then `Beat 1`, `Beat 2`, … (each distinct step or argument), then `CTA` (the ask). Use what fits; not every reel has every section.
  - `text`: the **verbatim** transcript for that segment — split the real words, don't paraphrase.
  - `note`: one short phrase on what the beat is *doing* ("names the pain", "step 1 — setup", "FOMO close"). This is the "what's working" signal.

## 2. Gate

Keep only reels with `score >= 7 AND verdict == true`. Everything else: add its shortcode to `ledger.json` → `low_score`, write no note.

## 3. Research the tools (per keeper — optional but recommended)

For each named tool, do a quick **web search** (don't rely on memory — these move fast): what it is in one line, how it works, one hook-worthy fact. Keep source links.

## 4. Write one note per keeper → `notes/SCRAPED-{date}-{username}-{slug}.md`

`slug` = topic lowercased, non-alphanumerics → `-`, max 50 chars.

```markdown
---
source_account: {username}
source_url: {url}
source_views: {views}
source_likes: {likes}
source_comments: {comments}
relevance_score: {score}
date_scraped: {date}
topic: "{topic}"
tools: "{tools joined by ', '}"
hook_style: {hookStyle}
---

# {topic}

## Source

- **Account**: [@{username}]({url})
- **Views**: {views} · **Likes**: {likes} · **Comments**: {comments}
- **Caption**: {caption, newlines→spaces, first 280 chars}

## Transcript (by section)

**Hook** — {note}
> {verbatim text}

**Beat 1** — {note}
> {verbatim text}

(…one block per section, end with…)

**CTA** — {note}
> {verbatim text}

## Research

- **{tool}** — {one-liner}
  - How it works: {mechanism}
  - Hook fact: {fact}

**Angle suggestion**: {one honest content angle for YOUR NICHE — a gap the competitor left open, not a copy of their reel}

## Production notes

- Hook style: {hookStyle}
- Relevance score: {score}/10
```

## 5. Update the ledger

Move each processed shortcode from `scraped` → `processed` (keepers) or `low_score` (rejects) in `ledger.json`. This is what makes the next scrape only pay for new reels.

## 6. Rebuild the dashboard

Then follow `DASHBOARD-SPEC.md` to regenerate `dashboard.html` from everything in `notes/`. Open it in a browser.

> The notes are *research artifacts*, not scripts. When an idea graduates to your own content, write it in your voice — the angle suggestion is the seed, never the copy.
