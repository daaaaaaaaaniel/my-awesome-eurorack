# STATE — where the work stands

Read this first when resuming. `CLAUDE.md` holds the rules; this file holds progress.
Update it whenever a phase finishes or a decision lands.

_Last updated: 2026-09-26 12:55 Helsinki — 993 rows (p1–p1096; p951–p1046 reserved for the review branch); `data/needs-ruling.tsv` holds 131 questions for d; exclusions are recorded per CLAUDE.md hard rule 5._

## Status

| phase | state | output |
|---|---|---|
| 0 — conventions | done | `CLAUDE.md` |
| 1 — harvest | done | `data/inventory.tsv` — 331 star-list repos (+ user-added ones, `page = user-added`), all resolve via `git ls-remote`, SHAs pinned |
| 2 — triage | **done** — all rulings in | `data/triage.tsv` → `triage.md` (`python3 data/triage_md.py`) — 325 IN / 34 OUT / 3 DEFERRED of 362 repos (331 starred + 31 user-added); 1,468 module dirs detected (upper bound) |
| pilot | done, corrected once | 13 rows from a 31-repo seeded sample (`data/pilot-sample.tsv`) |
| 3 — bulk enrich | **done** except d's rulings — 993 rows (2026-09-26 12:55); 131 questions wait in `data/needs-ruling.tsv` | `data/modules.tsv` |
| prefetch (evidence for 3) | **done** 2026-09-26 — all 1,305 todo dirs of `data/runlist.tsv` (v18 at pinned SHAs); 1 unreachable repo (triglav-modular/Voltage_Processor, 404) | `data/components-out.tsv` (SMD 382 / THT 214 / both 146 / blank 563), `data/readme-extracts/` |
| 3b — THT/SMD Pass B | not started | |
| 4 — dedupe + merge | not started | |

## Who runs what

- **The bulk run is run by the Opus session only** (user, 2026-09-26), starting on the user's
  command. Other sessions review and leave notes in `folder-bus-2/messages/`; they do not run
  the detectors or push to `claude/work-handoff-chat-i8tz65`.
- **Overnight run, 2026-09-26 (user, 05:16-05:33 Helsinki): GO.** Scope: ALL "todo" rows of
  `data/runlist.tsv`, every tier, in tier order (~1,305 dirs; the runlist is the count). Deadline
  **15:00 Helsinki = 12:00 UTC** (weekly reset): get as close to done as possible. Order: v19 +
  its re-prefetch first (done or in progress), then the enrichment chunks.
- **Check-ins never stop the run.** A scheduled "bulk-run check-in" (every 40 min) resumes work if
  it stopped silently. It ends the run ONLY when no "todo" rows remain or a note from d in
  `messages/` says stop - never because a chunk failed, a repo was hard, or it is unclear what
  "finished" means. If a check-in arrives mid-work: keep going, reschedule the next one.
- Rows that need d's ruling are skipped and logged (`data/needs-ruling.tsv`), never waited on.
  Never spend 15+ minutes on one module: log it as a follow-up and move on.

## Blocking decisions (the user's call)

1. ~~Scope~~ — **decided (user, 2026-09-26): take everything ruled IN**; no global
   re-count. The count itself is not needed; progress on extraction is.
2. ~~Curated `crimps` row~~ — **decided (user, 2026-09-26): `SMD`.** Applied as the first
   `CURATED_OVERRIDES` entry in `generate.py`. Footprints: 58 SMD + 4 THT
   (2 radial electrolytics, 2 DO-41 diodes). Jinx followed (user). The rule now allows
   **up to 5 THT passives**, and **any THT IC beside SMD parts means `both`** (user) —
   THT transistors count toward the 5 (user); `detector_version` 9 reports
   `tht_passive` / `tht_transistor` / `tht_ic`, telling transistors from TO-92 regulators by
   reference designator (`Q…`). Borderline calls are queued per module as a
   **"review components"** follow-up in `enrichment-audit.md` (currently: Precision Adder). Crimps and
   Jinx are `SMD` by the rule itself, no longer exceptions. (Brief v5 power-entry and v6
   10%-proportion experiments were reverted.)

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
  - ~~Delay~~ — **decided (user, 2026-09-26): IN.** Its DSP MCU board is proprietary (not in
    the repo); `License` records the split and `notes` link the board's product page.
  - ~~Output~~ — **decided (user, 2026-09-26): stays `both`** (1 SMD LM4808 + 74 THT).
  - **Swamp**'s BOM has no Package column → components blank, queued for Pass B.
- **`pixiemars/GMSNPure` — done** (p119–p125): 7 zips, one module each, **Eagle** `.sch`/`.brd`
  (not KiCad). Packages from the `.brd` XML, part-name packages resolved by the BOM PDFs in the
  repo root. Power Strip blank (OS-CON package unstated). Listing in `data/zip-contents/`.
- **`Mental-Noise/*` — done** (p116–p118) via the new EasyEDA source in `components.sh`
  (`data/easyeda_parts.py`); it also filled Testbild headphone (p10: `THT`).
- **`odeliy/schema-cave` — done** (p126–p170): 45 schematic-only modules; `schematic?` and
  `link` point to each PDF. Components only for Loafers (footprints printed) and Kick VCD+
  V1_THT / V2_SMD (file names). Juno-106 voice chip flagged: may not be a eurorack module.

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

- **monome Ansible: `runes.brd` is part of Ansible** (user, 2026-09-26), not a separate module.
  One row (p13), both boards counted together; `notes` names the runes board.

- **`schematic?` holds a link to the schematic file** when one exists as a standalone
  PDF/image (user, 2026-09-26); `x` only when it is implicit (inside EDA sources or a zip).
  Applied to the 13 pilot rows: 10 now link, Jinx / MiniDrumkit / Ansible stay `x`.
  Rule in `CLAUDE.md`, enforced by `generate.py`.

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

- **TO-92 / TO-220 parts never decide the SMD/THT call** (user, 2026-09-26 03:37): any
  number of them beside SMD parts is still `SMD`; DIP/SIP ICs and the 5-passive limit are
  the only things that make `both`. Supersedes the same day's "transistors count toward
  the 5" ruling and the Precision Adder precedent. Rationale recorded in `CLAUDE.md`
  ("What the labels are for"): the labels describe the soldering a builder faces.
  Applied in detector v15 (basis shows `tht_to=N`). Effect on existing rows:
  Mental-Noise/Axon `both` → `SMD`; Ansible blank → `SMD` (Strong); Synapse stays `SMD`
  (an unclassified package that cannot cross the 5 limit no longer blanks the call);
  Precision Adder stays `both` (8 passives); **tiny_rack v2 is `both` on 6 passives only
  if its three `biti:C286227` (KK1/3/4) parts and the Mean Well DC-DC brick count as THT
  soldering — needs a part lookup / ruling.**

## Open questions from the rulings

All open questions live in `data/needs-ruling.tsv` (2026-09-26 12:55: 131). Groups: Rebel / TiNRS /
allcolours (prototype rule answers "row it"; X-vs-? marks await d's OK, review branch
`claude/review-rebel-erd-tinrs` holds the drafted rows), elektrophon content/old (27 legacy designs +
6 Fuzz pedal clones), dev boards made for one specific module (Addatone ARM_Dev_Board, Sol breakouts,
tkilla64 helpers), RebelTechnology VactrolMixer SMD board.

## Next steps (pilot phase — historical, done)

- **Finish the pilot sample before the bulk run.** 18 of the 31 sampled repos have no row.
  Most are legitimate, but no collection has been expanded yet, so the step most likely to
  go wrong at scale is still untested:

  | status | repos |
  |---|---|
  | **collections expanded 2026-09-26** (p37–p76, ≤10 modules each) | `BruteClaw/Analog-Synth` (5 SMD + 5 THT builds of ADSR/LFO/Noise/Notch/VCF), `spielhuus/elektrophon` (first 10 of `src/`), `Thorinair/Avalon-Harmonics` (first 10; CVMod8_V2 split into SMD + THT rows), `ltrooney/diy-synth` (3), `kevinkewang/tiny_rack` (PSU v1, v2), `AfterLaterAudio/Eurorack` (3), `jakplugg/Orgone-accumulator` (DIY 3.0) |
  | **written 2026-09-26** (p26–p36) | `bpcmusic/TXb`, `newdigate/teensy-eurorack`, `spherical-sound-society/vortex-generator`, `samjkent/modular-mixer` (one row), `WiggisModular/mmc` (2 PSU rows), `pingdynasty/Mix` (**4 modules**: Mix 01–04, one `hardware/` folder), `joranvg/test-3` |
  | correctly no row | OUT: `glitched0xff/Midi2euroPiW`, `mortonkopf/Teensy-eurorack-rotating-step-divider`, `DatanoiseTV/PicoADK-Eurorack-Module`, `VoltageFoundryMod/ForgeSeries-CLK` (covered by `ForgeSeries` apps/clk) |

  The user asked for collections to be capped at ~10 modules in the pilot. **Batch 1 (2026-09-26)
  finished all three:** Avalon's other 10 (11 rows, VU split SMD + THT), BruteClaw's other 17
  rows (Patch Bay one row for both folders), elektrophon's other 11 `src/` modules. Still
  **awaiting a user ruling**: BruteClaw's 29 `Unfinished Designs/`, elektrophon's ~34
  `content/old/` legacy folders, and whether elektrophon's `draft: True` modules (cp3, echo,
  funktion, kaos, threeler) stay in.

- **Lessons from the collections:** module text can live in `index.rmd` YAML front matter
  (elektrophon: title / subtitle / references / `draft`) — `extract.sh` now prints it as a
  `=== FRONT MATTER ===` section; beware copy-pasted front matter (resonanz, tiefpass, echo); one folder can hold two
  builds (Avalon CVMod8_V2: SMD + THT files side by side) — split by board file, never pool;
  DipTrace (`.dch` schematic, `.dip` PCB) is a design source too; a README can promise files
  the tree does not have (AfterLaterAudio Baker/Rainier: BOM only); a `.kicad_pcb` can be a
  51-byte LFS stub (ltrooney midi-to-cv v2).

- Expanding a collection now means one `owner/repo<TAB>module_dir` line per module into
  `data/components.sh` and `data/extract.sh`; both scope to that module only
  (`data/modulefiles.sh`). Verified on BruteClaw, Avalon-Harmonics and crimps.

- Then Phase 3 in batches: append to `data/modules.tsv`, run `data/generate.py`, commit per
  batch with its `data/` artifacts.

## Bulk run log (Opus, 2026-09-26)

- 05:40-06:18 Helsinki: main queue done with `data/cards.py` (review cards + drafts) and
  `data/commit_chunk.py` (decisions -> rows / skips / needs-ruling / deferred), ~66 chunks, each
  committed and pushed. Rows p171-p764 (594 new); 407 skips with reasons (`data/skips.tsv`);
  248 deferred (`data/deferred.tsv`, not a ruling - work left for Opus); 67 logged for d
  (`data/needs-ruling.tsv`, mostly the already-pending BruteClaw Unfinished / elektrophon old).
- Conventions used, all in the row data: lineage creators "<original> + <this version>"
  (HAGIWO, Mutable Instruments, Rene Schmitz, Music From Outer Space, Look Mum No Computer...);
  width/THT/SMD variants one row each with "See alt. version"; revisions -> newest folder row,
  older ones skipped as superseded; sub-boards in sibling folders pooled (`"pool"` decision);
  firmware-per-hardware rows (HAGIWO 009/030, 029/033; 4ms RCD/SCM).
- Forks: poetaster/sluisbrinkie (fork of niektb) and FuturePresentLabs/mia-eurorack (fork of
  pichenettes/eurorack) skipped as duplicates; caseyjholmes/ADSR = kraakenstuff/ADSR flagged.
  Mutable Instruments rows take their part counts from the mia fork's Eagle XML copies (the
  original .brd files are old binary Eagle) - stated in basis and follow-up.
- Deferred blocks for dedicated passes: ThisIsNotRocketScience/Eurorack-Modules (dev dump),
  RebelTechnology/RebelTechnology (prototypes, many not eurorack), microresearch/allcolours
  (no READMEs), GroundGrown/eurorack-modules (69 boards flat), DrJ3RK, Bastl legacy archive;
  plus ~70 single modules whose function is not stated in the text read so far.

- 06:18-07:10 Helsinki: deferred pass done - `data/deferred.tsv` is empty. Rows p765-p950.
  Every runlist `todo` row (194) now sits in `data/needs-ruling.tsv`, waiting on d. Most of them
  collapse to four questions, and one answer settles each whole group:
  TiNRS Development dump (52 folders), microresearch/allcolours (36), Rebel Technology
  prototypes (33 + VactrolMixer SMD board), plus the older BruteClaw Unfinished (31) and
  elektrophon old (34). Smaller rulings: Deftaudio CV/Gate Attenuator (3), vauxflores CascaMesa +
  XimeTron/Eyecillator format (existing rows p545-549, p864-865 carry a follow-up: the maker site
  says XimeTron is its own acrylic instrument and Eyecillator a standalone 9V synth), promesoft
  YuSynth trio, yorkmodular HP pair, L71 passive_dist, DrJ3RK schematic-only circuits.
- Bastl legacy archive: 27 rows from the per-module PDFs + Knit Rider Eagle files; Dude, Klik,
  60KNOBS, Kastle, softPop, bitRanger, OMSynth are standalone instruments (no rows).
- Forge: one row per firmware app under `VoltageFoundryMod/ForgeSeries/apps/*` (6 + Expander 1),
  part counts from ForgeSeries-Hardware MainPCB/ControlPCB SMD V3.1.
- Types where the repo says nothing come from maker/retailer page titles (cited with URL in
  `type_basis`) or, marked "inferred:", from schematic labels/ICs.
- Lesson: WebFetch works unattended for URLs that appeared in a WebSearch result (provenance);
  a guessed URL needs d's approval and times out. Search first, then fetch the surfaced URL.
- `commit_chunk.py`: a re-defer replaces the old reason; a `module_dir` override now also sets
  the row's folder link. Keys whose row lives at another module_dir get a skip line pointing to it.

- 2026-09-26 11:45 rulings from d (applied on main):
  - Castor & Pollux expander -> "mentioned as a note associated with the main module": note on p11,
    hardware/expander skipped.
  - elektrophon content/old -> checked for newer versions: old funktion, hall and phasenregelschleife
    (PLL VCO) have newer src/ versions (p55, p56, p47) and are skipped as superseded. src/animation,
    filter, klang, synthese, verzerrung, midi are write-up pages (index.rmd), not newer hardware, so their
    content/old folders stay open with the rest of content/old (d's IN/OUT still pending).
  - Deftaudio -> "include the ones explicitly labeled as eurorack modules. Exclude the ones that have
    custom enclosures. Otherwise, leave the remaining ones to be reviewed." Eurorack_* folders already
    rows; enclosure skips: MIDITeensy3.2, MIDITeensy4.1, MidiThru4, MidiKnob, TRS_DIN5_Adapter,
    Teensy_1U_MIDI_8x14; 9 bare-board ones moved from skips to needs-ruling (9V_Converter, Korg DDD card,
    MIDITeensy4.0, MIDI_RS232, MidiAnySync, MidiMerge2in5out, MidiThru10, MidiThru2in10out,
    MidiThruWithMerge2in10out) plus the 3 CV/Gate Attenuators stay there.
  - yorkmodular resonant-filters: only 2 of the 3 described filters are in the repo - BPF (p890,
    resonant-bp + 2hp-bpf-panel) and HPF (new row p1047, mfrhp + rhpf panel). No LP board.
  - Row id p1047 skips p951-p1046, which are used on branch claude/review-rebel-erd-tinrs.

- 2026-09-26 11:51 rulings from d (applied on main):
  - promesoft KicadJE_MoogVCF -> three separate modules: rows p1065-p1067 (Moog VCF, JH wavefolder,
    555 ADSR) at KicadJE_MoogVCF_1_revB, one row each; part counts blank (one shared board).
  - L71 Eurorack_passive_dist.brd -> row p1068.
  - L71's other repos checked (GitHub API, all 26): eurorack ones added as user-added inventory + triage
    rows: 0x01_max261, 0x02_env, 0x03_2ch_quantizer, 1LFO, 2xVCA, 3xCV, ADSR2, BleepDrum-Eurorack,
    Logic (3 modules), MS20VCF, PolivoksVCF, ToneControl, XOR, lofisampler -> rows p1048-p1064.
    Rule "if its labled as a prototype, then don't include it": no repo is labelled a prototype;
    0x02_env and 3xCV say "work in progress" (rows kept, noted); ADSR2 uses adsr_v3 (adsr2 has
    "known design bugs", adsr2_v2 "will likely not be prototyped"); ADSR1 triaged OUT ("Deprecated ...
    replaced by the ADSR2 module"). Not eurorack / not modules (not added): AI-toolkit,
    ComputerHacks, EagleLibraries, containers, dnsmasq-viewer, l71.github.io, slacker (fork),
    stm32test ("Simple test synth engine"), tiny_avr_synth ("AVR test synth/MIDI beeper code").
  - Row ids continue at p1047+ so they do not collide with p951-p1046 on claude/review-rebel-erd-tinrs.

- 2026-09-26 11:56 rulings from d (applied on main):
  - DrJ3RK schematic-only circuits -> "include the schematics as long as their Eurorack-format circuits":
    rows p1069-p1075 (555 AD Envelope, Gene Splicer, PicoSubMix, Lockhart folder on +/-12 V; G&T,
    PicoVCO, one-pole LPG with +12/-12 rails plus a +15 label, noted). Excluded as +/-15 V only:
    MicroState, Mike Sims style VCA. New-Without-PCB-Schematic/WorkingDesigns is an empty 1-byte file.
  - vauxflores: CascaMesa and XT-09 Gold Standard excluded (skips); GS kept (row p934). The XimeTron /
    Eyecillator question for p545-p549 and p864-p865 stays in needs-ruling.

- 2026-09-26 12:00 d: "Eyecillator is a standalone synth, as is XimeTron, so they get excluded" -> rows p545-p549 and p864-p865 removed (ids retired, not reused); Eyecillator and all XimeTron folders in skips.tsv.

- 2026-09-26 12:15–12:33 rulings from d (applied on main unless noted):
  - Fable's `claude/modulargrid-rulings` merged (fast-forward a61d3b9): ModularGrid rows p1076–p1088,
    `prototype` column (10th CSV column).
  - Closed hardware: OUT unless a schematic is provided; with a schematic -> the non-open-source table
    (`claude/diy-commercial` c631–c641: Mini PEG, Pip, Penrose, Coven LFO, 7 Bastl). 17 triage OUT
    reasons rewritten with what was checked.
  - +/-15V circuits: OUT unless explicitly marked eurorack-compatible (DrJ3RK MicroState, Mike Sims VCA).
  - Prototypes: IN, marked in the prototype column. BruteClaw Unfinished Designs: Comb Filter p1089 (X);
    the other 30 folders are empty KiCad templates -> skipped. GMSN Pure Quantiser p1090 (X).
  - Deftaudio: remaining 12 boards OUT (non-eurorack). Tindie store check: Eurorack Ammeter p1093,
    MIDI BLE 2x2 p1094 (repo re-pinned 4e6e8dc -> a5cfa31); Luma-mu excluded (no schematic).
  - Added (d "yes add"): apfaudio/eurorack-pmod R3.5 p1096 (user-added), kxmx_bluemchen p1095.
  - Stale records fixed: rob-scape Daisy breakouts were skipped despite "Dev boards are IN" -> rows
    p1091–p1092; four more dev-board skips moved to needs-ruling; YuSynth's 13 unchecked pages checked
    (no eurorack option); prose-only exclusions (L71 non-module repos, elektrophon src write-ups,
    yorkmodular's missing low-pass) now have skips.tsv lines; conditions marked RECHECK ALLOWED.
  - CLAUDE.md hard rule 5: check the exclusion records before researching; don't re-open without d.

- 2026-09-26 12:39–12:50 (d): COEUR_MAIN.pdf is a schematic the name filter missed -> swept every row
  whose schematic was blank/x: 250 PDFs in 129 rows checked (pdfinfo Creator, text, rendered pages);
  69 rows now link their schematic (37 Eeschema, 7 KiCad macOS prints, 17 EAGLE/DipTrace/scan by text,
  8 by rendered page incl. gridbugs' KiCad 8 cairo exports). cards.py now lists unrecognised PDFs as
  "OPEN THESE PDFs"; CLAUDE.md working habit added. Dev/test boards made for one module excluded
  (d 12:42): Addatone ARM_Dev_Board, Sol breakouts x2, tkilla64 bb_helpers + rp2040_proto.
- 2026-09-26 13:24-13:57 (d): compared d's EurorackDIY Google Sheet (468 modules,
  docs.google.com/spreadsheets/d/1_euLePT_JGcswPoR7y1R5pLqPjAuCXZ5gZfOj9JKtqM) with every table:
  `data/eurorackdiy-sheet-compare.tsv` (one status per sheet row; 222 already covered). The sheet's
  schematic_url column misses schematics printed inside BOM/build PDFs (d 13:34, 13:35), so NLC and
  Isaac Beers were checked at the source: `data/nlc-schematics.tsv` - 156 NLC build PDFs rendered
  (pdf.js in the browser pane), schematic page found in 150; none in 1U MulCho, DP Filter, WAMOD Mixer;
  PARTS / Mults / De-Escalate / Covfefe have no PDF. `data/beers-schematics.tsv` - all 26 Isaac Beers
  products link a schematic PDF (10 of them are not in the sheet). Added to diy-commercial.tsv at 14:36 (below).
  14:00-14:30: other absent vendors checked at the source -> `data/vendor-schematic-checks.tsv`.
  Schematics published: Neutral Labs Meg/Nermal/Nijel/Scrat, Synthrotek APC/DIRT/ECHO/Sequence 8 (+308,
  Quadrangle, Combine-OR, Either-OR, VCA not in the sheet), CCTV Filther, David Haillant all 4. None:
  WGD (85 pages), Zlob (53 photo build PDFs), Ginko (9 PDFs), Neutral Labs Luna/Scrooge/Elmyra 2, Synthrotek
  DS-M/MST x4/VCO, 4ms PEG + QCD Expander, CCTV Immutable x7/O&C/Nerve Center/Out/Simple Gates.
  Frequency Central not checked (Cloudflare bot check).
  14:30-14:50: Erica EDU manuals carry the full schematic after the assembly appendix (11 of the 12 sheet
  EDU modules + Hi-Hat/FM Drum/Snare/Drum Mixer; Noise/S&H manual is 1 page). Hack Modular's Drive folders
  hold schematic PDFs. HexInverter Jupiter Storm manual: none. Found open GitHub hardware while checking:
  terrabite3/Affine, dhaillant/simple-lfo (CC-BY-SA 4.0), Simple-VCO, simple-vca -> NEW REPO rows in the compare.
- 2026-09-26 14:36-14:55 (d): "add the commercial modules that have a schematic" -> `claude/diy-commercial` c642-c704
  (63 rows: Beers 26, Erica EDU 15, Synthrotek 9, Neutral Labs 4, Hack 2, 4ms 2, BMC024, Lunch Bus, Moffenzeef,
  Filther, DM77). d 14:39: Mechlab Industries Eurorack Schematics -> c705-c755 (51 rows, lineage in notes; d 14:42
  one subagent per page, evidence in data/mechlab/ on that branch). The 8 modules missed by module detection are
  p1097-p1104 here. The compare file marks all of these HAVE. Open for d: schematic links on the NLC rows; log the
  ~110 no-schematic vendor modules as excluded; the ~46 NEW REPO rows (outside the star list) need d's go-ahead.
- 2026-09-26 15:03-15:25 (d): Dual VCA read `both` on smd=798 -> detector v20. Two faults: (1) SparkFun pin
  headers (`1X03`...) were counted as THT passives in Eagle; E2_PANEL now matches `:[0-9]+x[0-9]+`; (2) the
  DualVCA folder's 5 boards were pooled - `data/comp_pins.tsv` pins p596 to the Top+Bottom pair (git history:
  final design). Re-ran the 207 Eagle rows with `rerun_rows.py --basis=eagle --pin-all` (each row on the files it
  recorded; the unpinned re-run pooled flat folders - GroundGrown 71 files - and was rolled back). rerun_rows.py
  also fixed for records spanning lines and tabs inside quotes (p292's bom had been overwritten; repaired).
  Verdicts: both -> SMD for Dual VCA, Porter, Wizard, Genius (RebelTechnology), jhbruhn out, tiny_rack PSU v1;
  jhbruhn bus THT -> blank (headers only). d 14:57 via Fable 1458: p73 Baker / p75 Rainier creator
  `Mutable Instruments + Jim Mattheson + After Later Audio`.
- 2026-09-26 15:44 (d): iBOM HTML files were not counted as BOMs. Checked every HTML file in the repos of the
  476 `bom = -` rows by content (151 fetched: 132 iBOM, 7 other HTML BOM tables). 25 rows -> `bom = y`, files in
  `data/html-boms.tsv`: 16 inside the module folder (mzuelch x9, backtail mHz, chairaudio ILSE, MiniSNH, Vulcan DCO,
  tkilla64 bmult/vc-lfo, TINRS Set 9), 9 just outside it (BleepSound MS-20, backtail 6hp-psu/strg-m, and 6
  PierreIsCoding rows whose module_dir is the `pdfs/` subfolder - a moduledirs mis-split, so those rows' other
  fields were scoped too narrowly as well). cards.py now takes HTML in `bom/`/`ibom/` folders.
  -> done in v21 (next entry).
- 2026-09-26 15:48-16:30 (d): detector v21 - iBOM pads as a components source, HTML table BOMs via html2tsv.py,
  "switching diode" fix. Re-ran the 296 rows on BOM/no-source paths (recorded files + HTML). 37 blank rows now
  decided (THT 16, SMD 12, both 9: PierreIsCoding x9, tkilla64 x16, BurningForceKin x5, Vult x3, SourceryOne x2,
  yorkmodular yavcf), 10 BOM-decided rows moved to their iBOM with the same verdict, no verdict flipped; blanks
  346 -> 309. Of the 25 html-BOM rows only p675 (Single Attenuator: fader + jacks only) and the bus boards
  (Clacktronics Power Bus, jhbruhn bus) stay blank - nothing but panel hardware to count. Vorg is `both` on one
  SMD part (Q1 BCM857DS, SOT-457). Distortion and Wesp pinned to their V2 iBOMs (comp_pins.tsv).
- 2026-09-26 16:09-16:45 (d) Pass B start. Trial of 10 (data/passb-trial.tsv). d 16:15: count holes; d 16:23:
  verified no-SMD boards (incl. panel-only) are THT -> detector v22: panel-only footprint rows THT, gerber
  paste+drill source. Re-ran the blank rows: 17 decided, all THT (7 gerber, 7 Eagle, 3 iBOM panel-only), no
  flips; blanks 309 -> 292. Gerber notes left on 30 blank rows (26 no paste layer, 4 real SMD pads).
  Not done yet: .kicad_sch footprints (28 rows, 1 trial hit: p357 SMD), part-number lookup for the 23
  BOM-no-package rows, DrJ3RK's shared BOMs.txt (23 rows parse to 0 parts).
- 2026-09-26 15:25 (d): "Ornament & Crime" is the project, not a maker. p274 µo_C SE and p429-p431 O_C T4.1
  creator `Patrick Dowling + mxmxmx + Tim Churches + <porter>` (ornament-and-cri.me credit line); Mutable
  Instruments goes in notes only ("several apps reuse Mutable Instruments code"), not the creator (d: notes only).

## Multi-board folders (prep for the bulk run)

`python3 data/multiboard.py` -> `data/multiboard.tsv`: every prefetched folder with 2+ board/BOM
files, with a GUESS from filenames: `board+panel` (one board plus its panel PCB - not really
multi-board), `revisions`, `variants` (SMD/THT, stripboard), `sub-boards` (main + ctrl/io/...),
`collection` (different modules flat in one folder -> split per board with the filter column),
`unclear-pair`, or `mixed:`. The guess only orders the review; pending d's confirmation of the
0130 ruling, every multi-board row is flagged for manual check whatever the guess.

## Blank verdicts (prep for Pass B)

`python3 data/blanks.py` -> `data/blanks.tsv`: the 563 prefetched folders with no verdict, by
best remaining evidence: gerber/zip only 134, `.sch` without a board 116, BOM as PDF/HTML/md 80,
schematic PDF/image only 77, BOM spreadsheet (xlsx/ods) 70, KiCad schematic without board 46,
empty KiCad board 25, nothing hardware 10, Fritzing 3, other PDF 2.

Checked 2026-09-26 (Opus): the 116 `.sch` are 76 KiCad-legacy, 31 old binary Eagle (unreadable),
9 Eagle XML. A sample of 8 KiCad-legacy sheets: half hold no parts (top-level sheets) and the rest
have footprints on 2-48% of parts - too thin for a verdict; not worth a detector source.
Best recoverable set for Pass B: the 70 xlsx/ods BOMs (openpyxl and libreoffice are on the
device), then the 80 BOM documents.

Prototype 2026-09-26 (Opus, not adopted): `data/xl2tsv.py` converts xlsx/ods to TSV for
`bom_parts.py`; a scratch copy of components.sh reading `(bom|parts)*.xlsx|ods` gave 42 of the 70
a verdict (SMD 10, THT 19, both 13), 9 read with no classifiable lines (Vult Fuser/Wolv, Deftaudio
Teensy_5x5), 17 found no spreadsheet under the name pattern. Quality not good enough yet: the
Deftaudio BOMs read `tht_ic` high and passives at 0 (e.g. MIDI_RS232 tht_ic=2 passive=0;
MIDIThru4_TRS tht_ic=15) - look at those sheets' columns before wiring this in as v19.
Update (same night): cause 1 was an unrelated pin table pasted to the right of the BOM
(every row repeated "74HCT04 ... DIP?14"); `xl2tsv.py` now starts at the header row and keeps only
the header's columns -> MIDIThru4_TRS tht_ic 15 -> 2; totals now SMD 10 / THT 21 / both 2 / blank 37.
Cause 2 remains and is a real gap in the BOM path generally: Deftaudio sheets name no packages
("Resistor 220 Ohm"), so passives are silently unclassified and 12 of the 21 THT verdicts rest on
DIP-numbered ICs alone (tht_passive=0) - they could equally be "both". In the CSV BOMs this hits
only 1 of 100 prefetched BOM rows (and none of the 12 BOM rows in modules.tsv).
PLAN for v19 (not started): (a) read xlsx/ods BOMs via xl2tsv.py; (b) in the BOM path, count part
lines that match no SMD/THT pattern; if they could change the verdict (a THT/both call with
unclassified passives), leave it blank, Weak, "BOM names no packages for N parts" - same principle
as unclassified EasyEDA/Eagle packages. Then re-run the BOM rows.

## Known inconsistencies

- **Detector v18 (2026-09-26)**: mechanical parts excluded (heatsinks; `data/known_parts.tsv`,
  first entry LCSC C286227, user). Re-run of all 91 detector rows: only p72 tiny_rack v2 changed,
  both -> SMD (3 THT passives once its three heatsinks are excluded).
- **Detector v17 (2026-09-26)**: v16 + Fable's 157727d/e52da9b/f008d54 - user rulings 03:37-03:51:
  TO-92/TO-220 parts never decide SMD vs both (counted as `tht_to`, no ceiling); only DIP/SIP
  are THT ICs; from 10 TO parts on an SMD row a review note. Re-run of all 91 detector rows
  (in 4 parts - one shell call cannot outlive ~3 min): 3 changed, all by the TO rule -
  p116 Axon, p117 Synapse, p13 Ansible: both -> SMD. Every row now reads v17.
- **Detector v16 (2026-09-26)**: Fable's v15 (Eagle `.brd` read by `<smd>`/`<pad>` per package,
  portable lower-casing instead of gawk-only IGNORECASE, env-overridable prefetch paths) plus
  Opus's revision picker (`latest_files.py`) and review flag. All 91 detector rows re-run:
  4 changed - p13 Ansible blank -> both (Eagle; scope question runes.brd flagged), p26 TXb and
  p71 tiny_rack v1 same value now from Eagle (Strong), p72 tiny_rack v2 SMD -> both (three
  TO-220 LDOs the BOMs never listed). Opus's own name-heuristic Eagle draft was discarded.
- **Detector v14 (2026-09-26, `audit/fable-preflight`)**: v13 EasyEDA path + evidence fetched at
  the pinned `head_sha` (not the branch tip), `curl --fail` with explicit "fetch failed" /
  "no footprints" outcomes, no `head -4`/`head -2` caps, every file used named in the basis
  (`files=N: …`), BOM-path regexes (DIP8/DIL8/TO92 as THT ICs, stand-alone chip sizes,
  LEDs/pots excluded), and an optional third input column — a file filter — for folders that
  hold several boards (Avalon CVMod8_V2 / VU: `Main\.kicad_pcb$` vs `_THT\.kicad_pcb$`).
  Re-run over all 87 mechanically-derived rows: no verdict or confidence changed; bases
  rewritten in the v14 format. See `FABLE-PREFLIGHT-2026-09-26.md`; queue in
  `data/runlist.tsv` (`python3 data/runlist.py`), evidence prefetch in `data/prefetch.sh`.
- **Detector v15 (2026-09-26, `audit/fable-preflight`, draft for the Opus session to merge)**:
  **Eagle `.brd` read directly** (`data/eagle_parts.py`, step 1c after EasyEDA): mounting
  type comes from each package's own `<smd>`/`<pad>` elements, so it is explicit, `Strong`.
  62 IN repos / 297 dirs are Eagle-only and previously fell to the BOM path or Deferred.
  Also: every `IGNORECASE=1` in `components.sh` replaced by `tolower()` — IGNORECASE is
  gawk-only and **mawk (the cloud container's awk) ignores it silently**; the desktop VM has
  gawk, so rows computed there were unaffected. Re-run at v15 over the 82 tally rows: no
  verdict changed; three rows moved from BOM to Eagle evidence (Strong) and one of them,
  **tiny_rack v2 (p72), reads `both`** — its core board has three TO-220 regulators with IC
  references that the SMT-only BOMs never listed (rule: THT IC beside SMD → both; review).
  Existing Eagle rows: Benjolin `SMD` per revision (pool of 4 revisions reads both — use a
  filter on `benjolin_1.6.5.brd`); Ansible `ansible.brd` SMD, `runes.brd` both (1 THT IC).
  Rows still carry 14: relabel and re-run at merge time.
- **BOM parts are counted by the Quantity column** (else by designators) since
  `detector_version` 10 (`data/bom_parts.py`); previously BOM lines were counted.
- **Module detection v3 (2026-09-26)**: `src` is a container (elektrophon keeps its modules
  in `src/`) and `mount` is a part (a module's mounting board). Only elektrophon changed.
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
- `git ls-tree` writes non-ASCII paths **quoted in octal** (`"Fj\303\266l-v0.6/..."`) unless
  `core.quotePath=false`. 13 tree files held such paths, so those files never matched and a
  module dir read as empty (false absence); 4 module dirs were missing from the runlist.
  Decoded in place 2026-09-26; `clone_all.sh` now passes `-c core.quotePath=false`.
- A 7-char pinned SHA can be **ambiguous** in a big repo: raw.githubusercontent.com returns 404
  for `diysynth/EURORACK-MODULES@63c9945` (the API also refuses it). Its inventory SHA is now
  10 chars (`63c99450a5`). If a whole repo's fetches 404 at the pin, try a longer SHA.
- Filenames can start with a space (GroundGrown `" AC mixer v2 PANEL.brd"`); `read -r` without
  `IFS=` strips it and the fetch 404s. File loops in components.sh / extract.sh use `IFS= read -r`.
- device_bash kills everything at ~180 s. prefetch.sh workers now append their results as each
  finishes (Fable 0140); run it in slices (`RL=<slice>`), commit + push after each.
- "held no footprints": ~68 dirs have KiCad boards that are real empty placeholders
  (`(host kicad "dummy file")`, KiCad 8 empty boards) - schematic-only projects, not LFS stubs.
  Mostly BruteClaw (30, Unfinished Designs), gridbugs/briefcase-synth (13), elektrophon old (9),
  Schreibmaschine-Berlin (7). Read them as "no layout" at enrichment.
- `head -26` cuts into the last curated CSV row (embedded newline). Never slice by lines.
- 141 of 331 repos default to `master`; use the branch recorded in `inventory.tsv`.
- Re-run the detector over every affected row after any change; mixing versions shipped a
  wrong value at `Strong` confidence. `generate.py` now rejects stale `detector_version`.
- Read the README license grep, not just the LICENSE-file check (Ansible).
- Pinned SHAs were hand-typed for the pilot rows and 11 of 13 were invented. Copy every
  file-derived field by script; `generate.py` now checks SHAs against the inventory.
- Pooling a collection's PCBs gives every module one borrowed verdict. Scope per module.
