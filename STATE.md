# STATE — where the work stands

Read this first when resuming. `CLAUDE.md` holds the rules; this file holds progress.
Update it whenever a phase finishes or a decision lands.

_Last updated: 2026-09-25 — detectors scoped per module; invented SHAs replaced._

## Status

| phase | state | output |
|---|---|---|
| 0 — conventions | done | `CLAUDE.md` |
| 1 — harvest | done | `data/inventory.tsv` — 331 repos, all resolve via `git ls-remote`, SHAs pinned |
| 2 — triage | done, **rulings pending** | `data/triage.tsv`, `triage.md` — 289 IN / 21 REVIEW / 21 OUT, ~1,504 projected rows (upper bound) |
| pilot | done, corrected once | 13 rows from a 31-repo seeded sample (`data/pilot-sample.tsv`) |
| 3 — bulk enrich | **not started** — blocked on the decisions below | |
| 3b — THT/SMD Pass B | not started | |
| 4 — dedupe + merge | not started | |

## Blocking decisions (the user's call)

1. **Scope.** ~1,504 projected rows is an upper bound that includes known false positives
   (e.g. `ohmtech-rdi/eurorack-blocks`, a framework). Take everything, or filter harder?
2. **Triage rulings** — the 21 REVIEW repos in `triage.md`, plus "hardware but not a
   module" cases the pilot found but `data/triage.tsv` still marks `IN` (see
   *Known inconsistencies*).
3. **The curated `crimps` row** reads `THT` where its footprints say `both`: flagged, not
   edited (append-only rule). Leave it, or edit it yourself?

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
  Recorded in `data/triage.tsv`; `triage.md` is regenerated once the rulings are in.
- **Workshop Computer creator is `Music Thing Modular`** (user: Tom Whitwell's company;
  the README only says "Music Thing").

## Open questions from the rulings

None open. Remaining triage rulings are listed under *Blocking decisions*.

## Next steps (mine)

- **Finish the pilot sample before the bulk run.** 18 of the 31 sampled repos have no row.
  Most are legitimate, but no collection has been expanded yet, so the step most likely to
  go wrong at scale is still untested:

  | status | repos |
  |---|---|
  | **collections, never expanded** | `BruteClaw/Analog-Synth` (60 dirs), `spielhuus/elektrophon` (44), `Thorinair/Avalon-Harmonics` (20), `ltrooney/diy-synth` (7), `kevinkewang/tiny_rack` (power module only, v1/v2), `AfterLaterAudio/Eurorack` (3), `jakplugg/Orgone-accumulator` (2) |
  | single modules, not yet written | `pingdynasty/Mix`, `joranvg/test-3` |
  | ruled IN, not yet written | `bpcmusic/TXb` (i2c expander for Teletype) |
  | awaiting a ruling (decision 3) | `WiggisModular/mmc`, `newdigate/teensy-eurorack`, `spherical-sound-society/vortex-generator` |
  | correctly no row | OUT: `glitched0xff/Midi2euroPiW`, `mortonkopf/Teensy-eurorack-rotating-step-divider`, `DatanoiseTV/PicoADK-Eurorack-Module`; REVIEW: `VoltageFoundryMod/ForgeSeries-CLK`, `samjkent/modular-mixer` |

  The user asked for collections to be capped at ~10 modules in the pilot.

- Expanding a collection now means one `owner/repo<TAB>module_dir` line per module into
  `data/components.sh` and `data/extract.sh`; both scope to that module only
  (`data/modulefiles.sh`). Verified on BruteClaw, Avalon-Harmonics and crimps.

- Then Phase 3 in batches: append to `data/modules.tsv`, run `data/generate.py`, commit per
  batch with its `data/` artifacts.

## Known inconsistencies

- `data/triage.tsv` marks these `IN`, but reading them in the pilot says otherwise:
  `WiggisModular/mmc` is a case (out of scope);
  `newdigate/teensy-eurorack` is a Teensy shield (section 2); `spherical-sound-society/vortex-generator` says *"the hardware remains
  closed source, so please dont fabricate it"* — files present, but not buildable.
  Fix when decision 3 lands. The IN count (and so the ~1,504 projection) is inflated by
  cases like these.

- **Module detection mis-splits some single-module repos**, and scoping inherits that.
  `Testbild-synth/headphone`'s `design files/` folder is treated as a separate module, so
  its `.kicad_pcb` falls outside the root scope; `poetaster/noodle`'s gerber folders, and
  Addatone's `ARM_Dev_Board/` and `bu/` backup are split off too (the last two correctly).
  `wntrblm/Castor_and_Pollux` splits into faceplates, lens, interposer and **expander** —
  the expander may deserve its own row. Fixing `moduledirs.sh` is the "re-count" task, and
  it also shrinks the ~1,504 projection.

## Resuming in a fresh container

Everything durable is committed; the container is not. All scripts resolve paths from their
own location and work from any directory (verified 2026-09-25).

```sh
git checkout claude/work-handoff-chat-i8tz65 && git pull
python3 data/generate.py          # must print 26 frozen + N generated, no errors
git diff --quiet && echo clean    # regenerating must reproduce the committed files
```

- File trees for all 331 repos are committed in `data/trees/`, so triage and module-dir
  detection run offline: `bash data/classify.sh`, `bash data/moduledirs.sh owner/repo`.
- Network steps read stdin (`owner/repo` per line):
  `data/components.sh` (THT/SMD) and `data/extract.sh` (README/LICENSE/BOM signal lines →
  `data/readme-extracts/`). `data/clone_all.sh` skips repos whose tree already exists.
- Env overrides for testing: `INV`, `TREES`, `OUT` (extract), `WORK` (clone).

## Lessons already paid for

Each of these shipped a wrong value once. Details are in `CLAUDE.md`.

- Tab is IFS whitespace: bash `read` collapses empty TSV fields. Parse TSV in Python.
- `head -26` cuts into the last curated CSV row (embedded newline). Never slice by lines.
- 141 of 331 repos default to `master`; use the branch recorded in `inventory.tsv`.
- Re-run the detector over every affected row after any change; mixing versions shipped a
  wrong value at `Strong` confidence. `generate.py` now rejects stale `detector_version`.
- Read the README license grep, not just the LICENSE-file check (Ansible).
- Pinned SHAs were hand-typed for the pilot rows and 11 of 13 were invented. Copy every
  file-derived field by script; `generate.py` now checks SHAs against the inventory.
- Pooling a collection's PCBs gives every module one borrowed verdict. Scope per module.
