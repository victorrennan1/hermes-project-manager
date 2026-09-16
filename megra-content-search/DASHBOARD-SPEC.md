# Dashboard spec — what Claude builds from your notes

Say: **"Build the dashboard following DASHBOARD-SPEC.md."** Claude reads every note in `notes/` and generates a single, self-contained **`dashboard.html`** — no server, no build step, just open it in a browser.

It's a **static snapshot**: the data is embedded in the file at build time. After each new batch is processed, ask Claude to rebuild it and refresh the browser.

## Layout — two tabs

### Tab 1 — Dashboard (the daily read)

Top to bottom:

1. **KPI tiles** (animate: count up on load) — total reels tracked · accounts tracked · combined views · top reel's views · most-common hook style this batch.
2. **Reach by account** — horizontal bar chart (bars grow from zero on load): total views per account. This is your "who's actually pulling reach" view.
3. **Hook taxonomy** — one card per hook style (`problem-promise`, `contrarian-claim`, `list-tease`, `demo-first`, `story-frame`, `data-shock`, `identity-call`, `other`) showing count + combined views. Sort by combined views — this is the "which hook style wins in my niche" answer.
4. **Reel cards** — every note as a card, sorted by views (desc). Each card: account · topic · views/likes/comments · hook-style tag · relevance score. **Click to expand**: the full sectioned transcript (Hook / Beats / CTA with their notes), the research block, and the angle suggestion. Collapse on second click.

### Tab 2 — Pipeline (how the machine works)

A horizontal node graph of the pipeline, drawn with plain HTML/CSS (no chart library needed):

```
[Scrape (Apify)] → [Transcribe (Scribe)] → [Claude: score + break down] → [gate ≥7] → [notes/] → [this dashboard]
```

Each node: name + one-line description + per-run cost (scrape = ~cents · transcribe = ~pennies · Claude stages = free). Animate the nodes cascading in left → right on tab switch.

## Design rules

- Light theme, generous whitespace, one accent color used consistently (pick one and stick to it), system font stack. No dark-mode toggle needed.
- Load animations matter — tiles count up, bars grow, cards fade in staggered. They make the thing feel alive without a single external dependency.
- Everything inline: one file, `<style>` + `<script>` embedded, zero CDN links (it must work offline).
- Mobile is a non-goal — this is a desktop review tool.

## Data contract

Claude parses each `notes/SCRAPED-*.md` frontmatter (`source_account`, `source_views`, `source_likes`, `source_comments`, `relevance_score`, `topic`, `hook_style`, `date_scraped`, `source_url`) plus the sectioned transcript, research block, and angle suggestion from the body. Missing fields render as `—`, never break the page.
