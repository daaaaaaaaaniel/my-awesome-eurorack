# Website — next steps

Branch `website`, generator `site/build.py`, output `docs/` (GitHub Pages, branch `website` / `docs`).
Live: https://daaaaaaaaaniel.github.io/my-awesome-eurorack/
Modelled on https://signalfunctionset.com/builds/ . Kept current by whichever session works on the site.

Rulings recorded here are d's; dates are Helsinki.

## Needs d's ruling (data layer)

- [x] **Type categories, multi-tag or primary bucket?** — *multiple tags* (d, 2026-09-26 13:20).
- [ ] **Review `data/type-categories.tsv`** — 753 draft rows, now in ModularGrid vocabulary (48 + 5 extras; d 2026-09-28 01:18); mark `status` `ok` (or fix `tags`) row by row or in bulk.
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
- [x] Build status: prototypes hidden by default (both marks), "prototypes hide | show" toggle, checking a mark shows
      only that mark and greys the toggle; counter says how many are hidden within the current filter (d, 2026-09-26 14:22).
- [x] Board part counts from `comp_basis` (Strong rows, 548): Parts column + sort, breakdown on module pages, `*` when
      several board files were summed (d, 2026-09-26 14:46). Pin counts don't exist; would be a new detector pass.
- [x] Maker names in the index (table and grid) link to `?maker=<name>`, one link per " + " part, alias-folded; module-page maker links now URL-encoded (fixes "Ornament & Crime") (d, 2026-09-26 15:17).
- [x] Schematic shown inline on module pages (d, 2026-09-26 15:41): images via raw.githubusercontent.com `<img>`; PDFs drawn with PDF.js 4.10.38
      (jsDelivr) from raw.githubusercontent.com (CORS *; GitHub forbids iframing both blob pages and raw files). 543 of 557 schematic URLs
      (486 PDF + 57 image; the 14 `.sch` stay links); all 543 returned 200, none LFS pointers, max 4.7 MB. Plain URL link kept.
      15:59 (d): desktop browsers with a built-in PDF viewer (`navigator.pdfViewerEnabled`, fine pointer) get the native
      viewer via a blob: iframe of the fetched bytes (zoom/search/pages); touch devices keep the PDF.js canvases. The blob
      URL is minted per page view. Viewer title shows the PDF's own title, or the blob id when it has none.
- [x] BOM row on module pages links the BOM files (d, 2026-09-26 16:07): label = type (iBOM, CSV, XLSX, PDF...), path beside it;
      iBOMs open via htmlpreview.github.io (GitHub shows HTML as source; githack dropped 16:27 - first-visit interstitial). Files from data/trees with cards.py's BOM rule; comp_basis-named
      file wins; a folder shared by several modules links only name-matched BOMs (none rather than wrong); old/obsolete/backup
      dirs dropped; rule also matches "bill of materials" / singular "part list" (16:32, EuroPi); each iBOM also gets a small "source" link to its GitHub file page (d 16:21). 449 pages linked, 76 bom=y rows keep the text (shared folders with unmatched names, BOMs inside zips).
- [x] Panel / HP / photos / build guides on the site (d, 2026-09-26 17:21), from the panel, photos, build columns (working
      branch 968cfd9 + d5953b8): index HP column + sort ("?" = panel files, HP not settled), "only modules with panel source
      files" checkbox (`?panel=1`; 411 rows; in the Build status section since 17:49); module pages get HP (measured/stated, from panel_basis), Panel files (design
      files linked, gerber layers collapsed per folder), Build guide and Photos boxes, and their evidence. About page explains them.
      One photo thumbnail per module (d 18:00/18:01): the likeliest front view by filename (front/faceplate/assembled up;
      back/side/pcb/board/soldered down; (SMD)/(THT) rows prefer their variant; else the first photo), resized on request by
      wsrv.nl (fit inside 400x360, webp, 2x srcset, lazy); nothing stored. Other photos stay links. Originals total 1.9 GB.
      Index table: first column shows the same front photo, 56x64 via wsrv.nl, lazy, links to the module page (d 19:42).
      Possible next: HP facet (ranges).
- [ ] Parts count incl. panel parts (d, 2026-09-28 00:37): site ready - counts_of() adds `panel=N` from comp_basis when
      present (module page shows the split, index tooltip says which). Needs the detector to record panel=N (spec sent to
      the data session, messages/2026-09-28-0045); d wants the full 700+ row rerun held until d says (00:39). Verdicts unaffected.
- [ ] "Download CSV of current filter" button on the index.
- [ ] Rebuild automation: GitHub Action on push to `website` runs `site/build.py` and commits `docs/`, so the site
      can't drift from the TSV. Tradeoff: the Action needs `contents: write`, and `docs/` becomes bot-committed.
- [ ] Panel images — last and optional. One image per repo README, licensing per image; a separate harvest task.

## Deliberately not on the list

SEO work, comments, a corrections form (repo issues do that).
- 2026-09-28 02:04 (d): STL panel files get a "View in 3D" viewer on module pages (three.js 0.170 from jsdelivr, loaded on click; model from raw.githubusercontent.com, Git LFS pointers retried on media.githubusercontent.com). 19 pages / 21 files. STEP (occt-import-js, several MB wasm) and 3MF not done.
- 2026-09-28 03:33 (d): KiCanvas schematic & board viewer merged from branch kicanvas-test: 256 module pages; KiCad 6+ boards only (data/kicad-versions.tsv); file links drive the viewer; coverage page docs/kicanvas-coverage.html; details and regression test in site/kicanvas/ (README.md, test/viewer.test.js).
- 2026-09-28 05:42 (d): Schematic field on rows marked x now links the file(s) holding the schematic, any format (KiCad 6+/5, Eagle, DipTrace, Fritzing, EasyEDA, the module zip); 404 of 418 rows; "open in the viewer below" where KiCanvas can show it. schematic_sources() in build.py.
- 2026-09-28 06:01 (d): Pages source = GitHub Actions (.github/workflows/pages.yml runs site/build.py on every push to
  `website` and deploys docs/). docs/ is no longer committed (.gitignore). To change the site: edit site/build.py or the
  data, run `python3 site/build.py` locally to check, commit WITHOUT docs/, push. A failed run leaves the last deploy live.
  Branch previews via raw.githack.com no longer work for `website` (no docs/ in git); a test branch can still commit its
  own docs/ for a preview. The workflow file can't be written through the bus bridge (.github is protected): edit it
  from a cloud clone.
- 2026-09-28 06:15 (d 05:54 via note 0557): SMT assembly from the CPL audit (data/cpl-rows|shipped|audit.tsv): index facets "SMT assembly" (fixed order) + "Part numbers" (a-z, kinds rank equal), table column SMT, module field + box #smt (grade, source, SMD count / back side, shipped CPL+BOM links at the pinned sha, cleanup footprints, stale-CPL note). Rows not in the audit = "not checked".
- 2026-09-28 06:45 (d 06:28-06:45): index - SMT column right after Mounting; "Part numbers" facet removed (kind stays in the SMT tooltip and on module pages); "Files in repo" facet right under Type; live facet counts: each facet recounts from the modules matching every OTHER filter (a facet in "all" mode includes itself), zero values dimmed, the panel-only checkbox count too. Counts now follow the hidden-prototype setting.
- 2026-09-28 07:38 (d): .ai panel files as thumbnails when a module has no photo (after SVG): Illustrator PDF-compatible .ai renders through wsrv (all 61 tested in a browser 07:34, d accepted the 4 weak ones); 34 modules gain a thumbnail (mostly Mutable Instruments).
- 2026-09-28 08:25 licences: merged working-branch licence re-scan (905dfa8b, 59 rows filled); 16 new licence strings added to license-map.tsv via license_map_draft.py --append (new families CC-BY-NC-ND, Unlicense; faceplate/user-guide scopes; jurisdiction ports); Mouser-cart BOM links live
- 2026-09-28 08:35 HP field shows only the value (18HP / not determined / no panel files found); measurement or statement stays in Evidence > Panel / HP (d 08:06)
- 2026-09-28 08:50 SMT filter: THT rows the CPL audit didn't read count as 'No SMD parts' (from Mounting), not 'Not checked' (d 08:22): Not checked 628 -> 493. BYOM Micro (THT, SMD JST-SH connector) stays Placement-ready pending d's ruling. Licences d 08:07/08:17 merged; 1 new map string
- 2026-09-28 09:00 0HP modules (d 08:24, 9 rows) merged: HP shows 0HP, sorts first; they don't count as 'ships panel files'
- 2026-09-28 09:10 module pages: SMT assembly, License and Evidence boxes moved below the schematic and KiCanvas viewer (d 08:40)
- 2026-09-28 09:20 module pages: Schematic & board viewer now above Schematic (d 08:45); KiCanvas theme stays Witch Hazel (theme attribute ignored; d: not worth a workaround)
- 2026-09-28 09:30 module pages: no SMT assembly box when the grade is No SMD parts (d 08:48); spec row keeps the value, without the details link
