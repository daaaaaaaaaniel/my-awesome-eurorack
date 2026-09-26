# Website — next steps

Branch `website`, generator `site/build.py`, output `docs/` (GitHub Pages, branch `website` / `docs`).
Live: https://daaaaaaaaaniel.github.io/my-awesome-eurorack/
Modelled on https://signalfunctionset.com/builds/ . Kept current by whichever session works on the site.

Rulings recorded here are d's; dates are Helsinki.

## Needs d's ruling (data layer)

- [x] **Type categories, multi-tag or primary bucket?** — *multiple tags* (d, 2026-09-26 13:20).
- [ ] **Review `data/type-categories.tsv`** — 749 draft rows; mark `status` `ok` (or fix `tags`) row by row or in bulk.
      Vocabulary and soft spots in `data/type-categories.md`. The site already shows the draft tags,
      labelled "draft", so they can be reviewed in context.
- [ ] **License families** — 42 recorded values → e.g. open-permissive / open-copyleft / non-commercial /
      custom-free-for-DIY / no licence named / not determined. Same shape as the type table.
      Also: is "no licence named" shown as a warning?
- [ ] **Difficulty tier** — derive SFS-style tiers (🧊…🌋) from the footprint counts in `comp_basis`
      (`smd=75 tht_passive=4 …`, ~550 Strong rows; blank otherwise)? Needs thresholds d agrees with and a
      decision that a *derived* value may appear on the site at all (first thing there that isn't a quote from a repo).
- [x] **Maker facet splits "A + B" creators** into separate makers, exact strings, deduplicated (d, 2026-09-26 13:26).
- [x] `Rene Schmitz` → `René Schmitz` merged via `data/maker-aliases.tsv` (d, 2026-09-26 13:29).
- [x] `mysticcircuits` → `Mystic Circuits`, `Allen-Synthesis` → `Allen Synthesis`, `nanassound` → `Nanas Sound` (d, 2026-09-26 13:29).
- [ ] **Remaining maker near-duplicate** — `gerb-ster` / `gerbster` (only as "Roland + …", 1 + 8 rows). Data as recorded; merging is a row in
      `data/maker-aliases.tsv` (site-side only; the CSV stays append-only), one ruling per pair.
- [ ] **Scope** — include the non-open-source makers table from `claude/diy-commercial` as a second section
      with a License filter (SFS does), or keep the site open-source only?

## Data gaps the pipeline owes (working branch, not the site)

- [ ] 337 rows with no mounting → phase 3b (Deferred pass). The site reflects whatever lands.
- [ ] 131 rows in `data/needs-ruling.tsv` — d's queue.

## Site work (no rulings needed)

- [x] Type facet with a "not mapped" bucket, reading `data/type-categories.tsv` (2026-09-26, draft tags).
- [ ] License facet once the license table exists.
- [ ] Maker pages `/maker/<slug>/` — one linkable page per maker with their repos and modules.
- [ ] Polish: facet-collapse threshold (currently ≤800 px, collapses in narrow desktop panes); schematic chip
      "schematic (PDF)" vs "schematic (in repo)"; favicon; "report a problem" link per module page → repo issues.
- [ ] "Download CSV of current filter" button on the index.
- [ ] Rebuild automation: GitHub Action on push to `website` runs `site/build.py` and commits `docs/`, so the site
      can't drift from the TSV. Tradeoff: the Action needs `contents: write`, and `docs/` becomes bot-committed.
- [ ] Panel images — last and optional. One image per repo README, licensing per image; a separate harvest task.

## Deliberately not on the list

SEO work, comments, a corrections form (repo issues do that).
