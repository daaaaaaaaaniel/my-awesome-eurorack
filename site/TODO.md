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
- [x] **Licences as grants, several per module** (hardware / firmware / panel) — d, 2026-09-26 13:37.
      Plan and rules in `data/licenses.md`; draft `data/license-map.tsv` (54 grants from 42 strings).
- [x] Waft: "Creative Commons / MIT" → MIT (software) + CC BY-SA (docs) per OSHWA UK000005; `source` column added,
      external evidence rule in `data/licenses.md` §8 (d, 2026-09-26 14:15).
- [ ] **Review `data/license-map.tsv`** — mark `status` `ok` (3 of 55 done). Judgement calls are only the `custom`,
      `unclear` and `not-open` rows and the scope readings listed at the end of `data/licenses.md`.
- [ ] **Terms vocabulary** — as drafted (permissive · copyleft/share-alike · non-commercial · public domain ·
      custom · none named · none found · not open · unclear), or fewer buckets? No "open source yes/no" boolean
      unless d wants one defined as "names an OSI/OSHWA-approved licence".
- [x] Sidebar shows **License terms (draft)** only; the per-family License facet is hidden (`?lic=` still works). UI spelling: "License" (d, 2026-09-26 14:17).
- [ ] **Split the license facet by scope** (hardware licence / software licence)? Only ~60 rows state a
      scope; unstated-scope grants would have to count under both. Deferred until the single facet annoys.
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
- [x] Licence + Licence terms facets, grant table on module pages, scope-suffixed chips (2026-09-26, draft).
- [ ] Maker pages `/maker/<slug>/` — one linkable page per maker with their repos and modules.
- [ ] Polish: facet-collapse threshold (currently ≤800 px, collapses in narrow desktop panes); schematic chip
      "schematic (PDF)" vs "schematic (in repo)"; favicon; "report a problem" link per module page → repo issues.
- [x] any/all toggle on the multi-valued facets (Type, Licence, Licence terms, Files, Maker); `<facet>_mode=all` in the URL (d, 2026-09-26 14:03).
- [ ] "Download CSV of current filter" button on the index.
- [ ] Rebuild automation: GitHub Action on push to `website` runs `site/build.py` and commits `docs/`, so the site
      can't drift from the TSV. Tradeoff: the Action needs `contents: write`, and `docs/` becomes bot-committed.
- [ ] Panel images — last and optional. One image per repo README, licensing per image; a separate harvest task.

## Deliberately not on the list

SEO work, comments, a corrections form (repo issues do that).
