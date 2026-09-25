# STATE — where the work stands

Read this first when resuming. `CLAUDE.md` holds the rules; this file holds progress.
Update it whenever a phase finishes or a decision lands.

_Last updated: 2026-09-26 — Erica Synths DIY: 12 rows written from the unpacked zips (p14–p25). Next: finish the pilot._

## Status

| phase | state | output |
|---|---|---|
| 0 — conventions | done | `CLAUDE.md` |
| 1 — harvest | done | `data/inventory.tsv` — 331 star-list repos (+ user-added ones, `page = user-added`), all resolve via `git ls-remote`, SHAs pinned |
| 2 — triage | **done** — all rulings in | `data/triage.tsv` → `triage.md` (`python3 data/triage_md.py`) — 309 IN / 34 OUT / 3 DEFERRED of 346 repos (331 starred + 15 user-added); 1,468 module dirs detected (upper bound) |
| pilot | done, corrected once | 13 rows from a 31-repo seeded sample (`data/pilot-sample.tsv`) |
| 3 — bulk enrich | **started** — `erica-synths/diy-eurorack` done (12 rows, p14–p25); rest after the pilot (scope: everything IN) | `data/modules.tsv` |
| 3b — THT/SMD Pass B | not started | |
| 4 — dedupe + merge | not started | |

## Blocking decisions (the user's call)

1. ~~Scope~~ — **decided (user, 2026-09-26): take everything ruled IN**; no global
   re-count. The count itself is not needed; progress on extraction is.
2. **The curated `crimps` row** reads `THT` where its footprints say `both`: flagged, not
   edited (append-only rule). Leave it, or edit it yourself?

## Zipped repos

Zips are unpacked **in the cloud container** (user, 2026-09-26), never committed. Only the
evidence comes back: `data/zip-contents/<owner>_<repo>.txt` lists every file as
`<outer.zip>!<path>` (nested zips as `…!<inner.zip>!<path>`), plus per-repo tallies.
`module_dir` is the zip name and `link` is the zip's `/blob/` URL (`generate.py` accepts
`/blob/` as a deep link).

- **`erica-synths/diy-eurorack` — done.** 12 zips → 12 rows. Every zip has an Eeschema-PDF
  schematic, PCB + panel gerbers and `.xls` BOMs with a Package column, but no KiCad source
  (`layout = gerbers`). Components from the BOM packages (`data/zip-contents/erica-bom-tally.txt`).
  Open points for the user:
  - **Delay** needs Erica's pre-programmed DSP MCU board, which is not in the repo. Kept as a
    row with a follow-up flag; OUT instead?
  - **Output** is `both` by the 3-part rule: its one SMD part is an LM4808 (SO-8); every
    passive is THT. The written definition of `both` speaks of passives only, so this is an
    edge case.
  - **Swamp**'s BOM has no Package column → components blank, queued for Pass B.
- Still to unpack: `pixiemars/GMSNPure` (7 zips). `Mental-Noise/*` need an EasyEDA JSON
  package parser (also fills Testbild headphone); `odeliy/schema-cave` is schematics only.

## Set aside for a later pass

Bucket `DEFERRED` in `data/triage.tsv` — excluded from the bulk run, not forgotten.

- **`suessspeise/sdiy`** (user, 2026-09-25) — ~40 strip/protoboard layouts of *other
  people's* designs. Each row needs the original designer's lineage
  (`<designer> + suessspeise`, `(modified)`), `layout = protoboard`/`stripboard`, and a
  dedupe against existing rows: the curated Skull & Circuits VCF-1 row already cites this
  repo, and several layouts may be alt. versions of designs already in the table.
- **`Syntonie/documentation`** (user, 2026-09-25) — primarily video modules, so mostly out
  under the video rule. Set aside rather than dropped: a later pass would pick out any
  non-video audio modules among its ~35 product folders.
- **`golkit1/Stripboard-Layouts`** (user, 2026-09-25) — an entire repo of stripboard layouts
  drawn from other people's schematics. Same work as sdiy: lineage per layout, dedupe.

## Decided

- **Brand names not found in the repo → use the GitHub owner** (2026-09-25), spelled
  exactly as on GitHub, and flagged in the audit follow-up so it can be upgraded later.
  Rule and guard are in `CLAUDE.md` / `generate.py`. Applied to the pilot: 6 rows flagged;
  `508 loop detected` and `Testbild synth` (prettified handles) corrected. Su Su keeps
  `Voxmachina` because the curated CSV rows for the same repo supply it.
- **Jinx and Crimps are separate entries** — Jinx keeps its own row alongside the curated
  Crimps row; do not merge them at dedupe.
- **Castor & Pollux is `SMD`** — verified by the user.
- **`bpcmusic/TXb` is IN** (user): an i2c expander module for Teletype, not a power bus
  board — so it is not part of the bus-board question.
- **`BastianSPCTRL/COEUR` is IN; 1U tiles are in scope** (user), marked `1U` in `notes`.
  Its one PDF is a KiCad-exported schematic, so a schematic alone is enough for a row.
- **`kevinkewang/tiny_rack` is IN for its power module** (user: a power module, not just a
  bus board). All its design files are the power PCBs (v1 main + expansion; v2 core + 170/250
  expansions); the 3D-printed case is out.
- **Cases are listed in `cases.md`** (user) — URLs only; 15 found across the star list.
  Left out as not-cases: standalone-device enclosures (Syntonie, Kastle 2, quadtec101, a MIDI
  box and a MIDI keyboard), tinrs' CaseBuilder tool, and two case accessories (AfterLaterAudio
  heatsink covers, Mystic Circuits "Case Upgrade Kit").
- **`shannon-greenlight/Melper` is IN** (user): a PSU.
- **Case/panel fabrication software is listed in `cases.md`** (user): EuroPanelMaker,
  EuroRailMaker, tinrs' CaseBuilder / FrameBuilder / Panelizer, and eurorack-blocks'
  generators (borderline — it is a whole code-to-hardware framework).
- **Bus boards are IN** (user) — `butchwarns/Eurorack_Bus_Board` is a passive bus board.
- **`newdigate/teensy-eurorack` is IN** (user): a proper eurorack module, typed
  `audio platform (Teensy 4.1)` (user).
- **Forge series: one row per firmware app** (user), notes citing `ForgeSeries-Hardware`.
  The per-module firmware repos the hardware README links (DQ, SCP, GEN) no longer exist; all
  apps now live in `VoltageFoundryMod/ForgeSeries` — ClockForge, NoteForge, GravityForge,
  ForgeView, ChaosForge, WeaveForge — plus Forge Expander 1 (hardware). `ForgeSeries` and
  `ForgeSeries-Hardware` were added to the inventory as `user-added` (not in the star list).
  ClockForge links to the current `ForgeSeries` `apps/clk` (user); the starred, archived
  `ForgeSeries-CLK` is OUT as covered.
- **`spherical-sound-society/vortex-generator` is IN** (user): schematic
  `Schematics_VortexGen_Rev2.02.pdf`. `License` must say the hardware is closed source per
  the README; proposed `open source, no licence named (firmware) / closed source (hardware,
  per README)`. Layout `commercially available` (Tindie kits). Rev 3.0 SMD has no schematic.
- **`westlicht/performer` is OUT; `performer-hardware`'s notes link it** (user):
  `https://github.com/westlicht/performer`.
- **`ohmtech-rdi/eurorack-blocks` is OUT** (user): a framework, not modules.
- **Tall Dog Electronics modules are IN** (user): uBraids SE, uClouds SE, uRings SE, uPlaits SE
  (after Mutable Instruments) and uo_C SE (after Ornament & Crime by Patrick Dowling,
  mxmxmx and Tim Churches — three designers, so they go in `notes` and `creator` stays
  `Tall Dog Electronics`). They live in five `loglow/*_SE` repos linked from
  `loglow/Tall-Dog-Public` (now OUT as an index repo); all five added as `user-added`.
- **`retoid/Module-Panel-Templates` is listed in `cases.md`** (user); no module rows.
- **cob333 `Pico-Eurorack` and `PicoPro-Eurorack` get no rows** (user); the
  `rheslip/2HPico-Eurorack-Module-Hardware` row's notes link both. Both READMEs confirm they
  are firmware for Rich Heslip's 2HPico hardware.
- **Fihdi's modules are IN** (user): BIPO, DICE, SCULPT, SVF12, UNO, VCAR — six repos linked
  from `Fihdi/Eurorack` (now OUT as an index repo), added as `user-added`; MiniDrumkit was
  already in the list. VCAR is based on the Serge DUSG. SCULPT has design files only.
- **`samjkent/modular-mixer` is IN as one entry** (user): one mixer made of modular
  sub-modules. Its KiCad files are in two submodule repos, added as `user-added` for evidence
  only (no rows of their own). User-supplied info page (web.archive.org, not fetchable here).
- **`WiggisModular/mmc` is IN for its PSU** (user); the case stays in `cases.md`. Two PSU
  builds (`psu/eurorack1A`, `psu/eurorack1A_SMD`) → two rows.
- **Dev boards are IN** (user): `rob-scape/daisy-seed-breakout-boards` → two rows typed
  `dev board (Daisy Seed)`; gerbers + BOM only, no schematic.
- **`OmsInSerial/Eurorack` is OUT** (user): FM/FX Einheit are not truly open source — the
  repo holds firmware `.bin` files and one CSV, no design files.
- **The last six REVIEW repos are IN** (user, 2026-09-25): `Mental-Noise/Axon`, `Synapse`,
  `Thal` (EasyEDA JSON sources); `pixiemars/GMSNPure` (7 zipped KiCad snapshots + BOM PDFs,
  GMSN + pixiemars lineage, self-described incomplete); `erica-synths/diy-eurorack`
  (11 module zips, unopened — row count unknown until expanded); `odeliy/schema-cave`
  (45 schematic PDFs of retired/unreleased modules). Triage is complete.
- **Video-synth modules are OUT** (user). `MartijnVerhallen/Video-Documentation` → OUT;
  `diyelectromusic/sdemp_pcbs` loses its `PicoVGABreakout` board when expanded.
- **Build-doc repos: a module is included only if its schematic is in the repo** (user).
  `MartijnVerhallen/Audio-Documentation`: of 10 projects only Busboy 9000 and Datura Nebula
  have schematics (every PDF's text and page-sized images checked). Datura Nebula is OUT
  (user: standalone synth, not eurorack) and Busboy 9000 is OUT (user: a video synth
  module), so the whole repo is OUT.
- **`bummbummgarage.github.io` stays IN** for the bulk run (user: not too complicated).
  When enriching: mostly `layout = stripboard` (+ gerbers for the 6 modules that have them);
  lineage for derived designs — each is stated explicitly in the module's `index.md`
  (not a README; `extract.sh` now reads it). Expected credits, per the user — check the
  enrichment output against this list:
  Ken Stone (gate-to-trigger converter), Music Thing Modular (Chord Organ), Robin Mitchell
  (exponential converter), Bastl Instruments (filter — PROPUST), René Schmitz (envelope
  generator — Fastest Envelope in the West; VCF — Korg late MS20 filter), Jens Moller
  (mixer), richardc64 and SyntherJack (noise generator), shiftr (`vca-0.1` — "1 transistor
  passive VCA-ish thingy"), Kristian Blåsol (`vca-0.2` — "Vactrol VCA") and Look Mum No
  Computer (`envelope-generator-II-0.1` — "Simple DIY Envelope Generator"), Haraldswerk
  (VC mixer/VCA), Doepfer (PSU3). Blåsol and Look Mum No Computer are the same person: both rows
  read `Look Mum No Computer` (user, 2026-09-25), with the page's wording kept in the basis.
  Collapse case-only duplicate folders (`envelope-generator-II-0.1` = `…-ii-0.1`), but
  **not version numbers blindly**: `vca-0.1` and `vca-0.2` are different circuits with
  different credits. Only merge versions whose credits and circuit match. Drop the 3 cases
  and the folders with no design files.
- **Triage ruling: `SonicPotions/Penrose` → IN.** Schematic is off-GitHub (user-supplied:
  sonic-potions.com/public/PenroseQuantizerSchematic.pdf), not fetchable from here.
  Recorded in `data/triage.tsv`.
- **Workshop Computer creator is `Music Thing Modular`** (user: Tom Whitwell's company;
  the README only says "Music Thing").

## Open questions from the rulings

None open. Triage is complete; the remaining user decisions are under *Blocking decisions*.

## Next steps (mine)

- **Finish the pilot sample before the bulk run.** 18 of the 31 sampled repos have no row.
  Most are legitimate, but no collection has been expanded yet, so the step most likely to
  go wrong at scale is still untested:

  | status | repos |
  |---|---|
  | **collections, never expanded** | `BruteClaw/Analog-Synth` (60 dirs), `spielhuus/elektrophon` (44), `Thorinair/Avalon-Harmonics` (20), `ltrooney/diy-synth` (7), `kevinkewang/tiny_rack` (power module only, v1/v2), `AfterLaterAudio/Eurorack` (3), `jakplugg/Orgone-accumulator` (2) |
  | single modules, not yet written | `pingdynasty/Mix`, `joranvg/test-3` |
  | ruled IN, not yet written | `bpcmusic/TXb` (i2c expander for Teletype), `newdigate/teensy-eurorack`, `spherical-sound-society/vortex-generator`, `samjkent/modular-mixer` (one row; evidence from its two submodule repos) |
  | ruled IN for its PSU (case in `cases.md`) | `WiggisModular/mmc` |
  | correctly no row | OUT: `glitched0xff/Midi2euroPiW`, `mortonkopf/Teensy-eurorack-rotating-step-divider`, `DatanoiseTV/PicoADK-Eurorack-Module`, `VoltageFoundryMod/ForgeSeries-CLK` (covered by `ForgeSeries` apps/clk) |

  The user asked for collections to be capped at ~10 modules in the pilot.

- Expanding a collection now means one `owner/repo<TAB>module_dir` line per module into
  `data/components.sh` and `data/extract.sh`; both scope to that module only
  (`data/modulefiles.sh`). Verified on BruteClaw, Avalon-Harmonics and crimps.

- Then Phase 3 in batches: append to `data/modules.tsv`, run `data/generate.py`, commit per
  batch with its `data/` artifacts.

## Known inconsistencies

- **Module detection v2 (2026-09-26)** — `moduledirs.sh` now treats any folder whose name
  contains `gerber` (`noodle-gerbers`, `Gerber_for_JLCPCB`), and generic `<x> files` folders
  (`design files`, `Eagle Files`, `PCB Files`, `JLCPCB fabrication files`), plus `assembly`,
  as parts of the module above them. 35 repos changed; every change was reviewed. Variant
  names are kept: `2HPico KiCad design files` vs `4HPico …` stay separate modules.
  The user chose **not** to re-count globally: remaining mis-splits are checked per repo
  as it goes through extraction.
- **Still split, check at extraction:** per-board sub-folders of one module
  (`rheslip/2HPico…`'s `Pico 2HP Controls` / `Pico 2HP_Audio`), and
  `wntrblm/Castor_and_Pollux`'s faceplates, lens, interposer and **expander** (the expander
  may deserve its own row).

## Resuming in a fresh container

Everything durable is committed; the container is not. All scripts resolve paths from their
own location and work from any directory (verified 2026-09-25).

```sh
git checkout claude/work-handoff-chat-i8tz65 && git pull
python3 data/generate.py          # must print 26 frozen + N generated, no errors
python3 data/triage_md.py         # triage.md from data/triage.tsv
git diff --quiet && echo clean    # regenerating must reproduce the committed files
```

- File trees for all 331 star-list repos (and the user-added ones) are committed in `data/trees/`, so triage and module-dir
  detection run offline: `bash data/classify.sh`, `bash data/moduledirs.sh owner/repo`.
- Network steps read stdin (`owner/repo` per line):
  `data/components.sh` (THT/SMD) and `data/extract.sh` (README/LICENSE/BOM signal lines →
  `data/readme-extracts/`). `data/clone_all.sh` skips repos whose tree already exists.
- Env overrides for testing: `INV`, `TREES`, `OUT` (extract), `WORK` (clone).

## Lessons already paid for

Each of these shipped a wrong value once. Details are in `CLAUDE.md`.

- `data/inventory.tsv` is committed with **CRLF** line endings: `awk '{print $7}'` returned
  `master\r`, so every raw fetch failed and every row came back `Deferred` with no error.
  `components.sh` / `extract.sh` now `tr -d '\r'`. Parse the inventory in Python, or strip `\r`.
  (Found 2026-09-26; rows already in `modules.tsv` were unaffected — re-run matched.)

- Tab is IFS whitespace: bash `read` collapses empty TSV fields. Parse TSV in Python.
- `head -26` cuts into the last curated CSV row (embedded newline). Never slice by lines.
- 141 of 331 repos default to `master`; use the branch recorded in `inventory.tsv`.
- Re-run the detector over every affected row after any change; mixing versions shipped a
  wrong value at `Strong` confidence. `generate.py` now rejects stale `detector_version`.
- Read the README license grep, not just the LICENSE-file check (Ansible).
- Pinned SHAs were hand-typed for the pilot rows and 11 of 13 were invented. Copy every
  file-derived field by script; `generate.py` now checks SHAs against the inventory.
- Pooling a collection's PCBs gives every module one borrowed verdict. Scope per module.
