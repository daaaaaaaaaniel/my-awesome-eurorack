# eurorack-open-source.csv — working conventions

Reference table of buildable DIY eurorack modules. This file exists so the conventions
survive across sessions; it is the authority when memory and chat history are gone.

**Progress, open decisions and how to resume live in `STATE.md` — read it first.**

## The deliverable

`eurorack-open-source.csv` — **exactly 10 columns, never more**:

    creator, Module Name, Type of Module, License, schematic?, layout, components, link, notes, prototype

Row 1 is the header. **Row 2 is a legend row** defining the base vocabulary
(`x | n/a`, `kicad | eagle`, `THT | SMD`, `X | ?`). Rows 3+ are module rows.

- **`prototype`** (user, 2026-09-26; the 10th column): **blank by default**. **`X`** when the repo
  clearly labels the build a prototype or untested ("NOT TESTED", "not yet built and tested",
  "work in progress", "prototyping stage", "don't build yet"). **`?`** when the wording is
  ambiguous - an unreleased folder, a `draft` flag, "this revision untested but earlier ones
  worked", a known erratum on a built prototype. Never inferred from a version number or from
  the absence of a statement. The evidence goes in `prototype_basis` in `data/modules.tsv`
  (a quoted line or file name); `generate.py` refuses a mark without one and prints it in the
  audit's Follow-up column. The curated 26 rows carry the column as an appended empty cell
  (`generate.py` adds it to their frozen bytes; the legend cell reads `X | ?`).

## Hard rules

1. **Never invent a field value.** A blank cell is correct; a guessed one is a lie that gets
   acted on when ordering parts. Blank beats plausible, always.
2. **Never edit existing rows**, or the header, or the legend row. Append only.
   The curated prefix is **26 logical CSV rows** — which span **27 physical lines**,
   because one `creator` field contains an embedded newline and the file has no trailing
   newline. **Never slice it by line count**: `head -26` cuts into the last curated row.
   `data/generate.py` copies the baseline commit's bytes instead, which is what makes
   append-only mechanical rather than a thing to remember.
   **The only exceptions are user-authorised edits listed in `CURATED_OVERRIDES` in
   `generate.py`** (exact substring, must match once). First: Crimps `THT` → `SMD`
   (user, 2026-09-26). Never add one without an explicit user ruling.
3. **Preserve exact column order**, and keep the column count at 10.
4. Every non-blank cell must be traceable to a file path in the repo tree or a quoted line
   of raw text. If neither exists, the cell is blank.
5. **Check the exclusion records before researching anything** (d, 2026-09-26). Before
   researching, adding or re-checking any repo, folder, maker or module, look it up in:
   `data/skips.tsv` (folders and file-level keys; includes checked repos that are not in the
   inventory), `data/triage.tsv` bucket `OUT` (whole repos), `data/needs-ruling.tsv` (already
   waiting on d), and on branch `claude/diy-commercial` `data/diy-commercial-excluded.tsv`
   (non-open-source makers). If it is there, **do not re-open it without d's say** — an
   exclusion is a ruling or a finished check, not a draft. The one exception: a reason marked
   **`RECHECK ALLOWED`** records a *condition* (repo unreachable, module unreleased, a file that
   could not be opened), and may be re-checked. Every new exclusion gets a line in one of these
   files with its reason and date (quote d when d ruled it); an exclusion that lives only in
   `STATE.md` prose does not count.

Existing rows contain a few typos (`function generaor`, `kidcad`, `stipboard`). Rule 2 means
they stay. New rows use correct spelling — do not replicate the typos.

## Table conventions

- **The unit of record is a buildable module variant, not a repository.** One repo can produce
  many rows (`musicdevghost/eurorack` is 6). One *module* can produce several when it ships as
  distinct builds — EuroPi is through-hole, surface-mount and stripboard, so three rows.
  **A version number is not proof of a revision**: bummbummgarage's `vca-0.1` (shiftr's
  1-transistor VCA) and `vca-0.2` (Blåsol's vactrol VCA) are different circuits. Merge
  numbered folders into one row only when their credits and circuit match.
- **`creator` carries lineage**: original designer `+` whoever made this version —
  `Rene Schmitz + Divergent Waves`, `YuSynth + thismatters`, `Mutable Instruments + Karltron`.
  Derived modules get `(modified)` appended in `Module Name`: `YASH (modified)`.
- **Where `creator`'s maker name comes from**, in order: a brand stated in the repo
  (README, LICENSE copyright line, shop links); the curated CSV's own rows for the same repo
  (`Voxmachina`); otherwise **the GitHub owner, spelled exactly as on GitHub** — never
  prettified (`508-loop-detected`, not `508 loop detected`). Record an owner fallback with a
  `creator_basis` containing "GitHub owner"; `generate.py` then flags it in the audit and
  refuses a creator that doesn't match the handle. Never infer a fuller name yourself;
  **the user's own knowledge is a valid source** — record it with a `creator_basis`
  starting `user:`. Precedent: the Workshop Computer README only says "Music Thing"; the
  user supplied `Music Thing Modular` (Tom Whitwell's company). Where both a person and
  their company are candidates, that precedent chose the company — confirmed again for
  Kristian Blåsol → `Look Mum No Computer`.
- **One hardware platform, many firmwares → one row per firmware**, with `notes` citing the
  hardware repo (user, 2026-09-25). The Forge series is the example: `ForgeSeries` holds one
  app per module (ClockForge, NoteForge, …) for the shared `ForgeSeries-Hardware` board.
- **Hardware and firmware in separate repos, one module** → one row for the hardware, whose
  `notes` link the firmware repo (user, 2026-09-25: `westlicht/performer-hardware` notes link
  `https://github.com/westlicht/performer`). The firmware repo itself gets no row.
- **One module built from sub-boards in git submodules** → a single row for the parent repo,
  with its evidence read from the submodule repos (user, 2026-09-25: `samjkent/modular-mixer`).
- **Repos outside the star list** may be added when the user asks (e.g. the Forge repos).
  They go into `data/inventory.tsv` with `page = user-added`, so SHA and link checks work.
- **`Type of Module` must state a function.** Never `eurorack module`, `module` or
  `synth module` — everything in this table is a eurorack module, so it says nothing.
- **`Type of Module` uses eurorack-native vocabulary**, not generic categories: `S&H`,
  `VCF (vactrol)`, `LPG (vactrol/passive)`, `Bernoulli Gate`, `Analog Shift Register`,
  `PT2399 delay`, `VCA (quad)`. Compound types slash-joined: `S&H / Noise / Rectifier / Logic`.
- **`link` is a deep link** — the specific subdirectory, PDF or product page. Never a repo root.
- **`schematic?` links to the schematic itself** (user, 2026-09-26) when the repo has a
  standalone schematic file: a `/blob/` deep link, preferring a PDF, otherwise an image
  (`.png`/`.jpg`/`.svg`). Link the current revision, and check a file actually is a
  schematic before linking it (an untitled PDF can be a placement drawing; a PNG a block
  diagram). Write **`x`** when the schematic is only implicit — packaged inside KiCad,
  Eagle or EasyEDA sources, or inside a zip — so there is no proper path to point to.
  `n/a` / blank as before. The curated 26 rows keep their `x` (append-only); the legend
  row is unchanged. `generate.py` rejects any other value.
- **Schematic split over several files** (user, 2026-09-26 05:51): a module with 2+ PCBs in the
  same revision (stacked boards) whose schematic is not one file keeps a single value in
  `schematic?` - `x`, or a link to one of the files (prefer the main board's; the column
  validator accepts one link) - and the complication is noted in the row's follow-up with every
  schematic file named. `generate.py` adds that note automatically ("schematic split over N
  files") for rows that have their folder to themselves; split rows sharing a folder get it by hand.
- **`layout` extends past its legend** in practice, and this is the idiom for recording
  fabrication files too: `easyEDA + gerbers`, `kicad + stripboard`, `stripboard`, `protoboard`,
  `commercially available`, `n/a`. **Gerber availability is recorded here as `+ gerbers`** —
  there is deliberately no separate column for it.
- **`notes` carries cross-references only**: "See alt. versions from…", "based on X design",
  and lineage with **more than one ancestor** (vca-8 draws on YuSynth *and* Kassutronics, so
  `creator` stays `Polykit` and both sources go here — `creator` keeps its
  `original + this version` shape). Not board names, licence detail, or repo trivia.
  **A required proprietary part is noted too** (user, 2026-09-26): Erica Delay's notes link
  the closed DSP MCU board it cannot be built without, and `License` names it `proprietary`.
  **One format marker is allowed: `1U`** for 1U tiles, which are in scope (user,
  2026-09-25 — BastianSPCTRL/COEUR).
- **Multi-licence repos record the full split in `License`**, e.g.
  `CERN-OHL-P v2 (hardware) / CC BY-SA 4.0 (panel) / MIT (firmware)`. Never in `notes`.
- **Lineage is often at the END of a README**, in a `# References` / `# Credits` section as
  bare URLs rather than prose. `data/extract.sh` greps for those headings and for known
  designer domains; do not rely on "based on" appearing in the text.
- **Module text is not always in a README.** GitHub Pages sites keep each module's page in
  `index.md` (bummbummgarage.github.io's design credits are all there); `extract.sh` falls
  back to `index.md` inside the module before the repo-root README.

## components — THT / SMD / both

- **`THT`** — the build uses *exclusively* through-hole components.
- **`SMD`** — uses surface-mount ICs, or surface-mount resistors/capacitors/diodes/passives.
  **THT jacks, switches and pots do NOT disqualify an `SMD` marking** — nearly every SMD
  module uses through-hole panel hardware. **Panel hardware is excluded from the THT tally
  entirely**: pots, jacks, switches, buttons, LEDs, pin headers, sockets, encoders,
  displays, mounting holes, test points and fiducials never count as THT parts.
  (MiniDrumkit's only "THT" parts are 12 pots + 8 LEDs + 4 pots — it is `SMD`.)
- **`both`** — SMD parts together with a THT IC (DIP/SIP), or with more than 5 THT passives. (Extends the legend's `THT | SMD`;
  the legend row itself stays byte-identical per rule 2.)
- **What the labels are for** (user, 2026-09-26): `THT` tells a builder they will not need
  the tools associated with SMD soldering; `both` tells them some SMD soldering will be
  required alongside a real amount of THT work; `SMD` tells them very little THT soldering
  is required. The thresholds below are mechanical proxies for that — when a part is
  ambiguous, ask whether it adds meaningful THT soldering, not what its package is called.
- **The threshold** (user, 2026-09-26; was 3 parts in `a5e93ec`): after excluding panel
  hardware, a build with SMD parts reads **`SMD` when it has at most 5 THT passives** and
  **no THT IC**. **Any THT IC (DIP/SIP, socketed or not) beside SMD parts makes it
  `both`** — even a single one. Six or more THT passives also make it `both`.
  **TO-92 / TO-220 (and TO-3) parts never decide** (user, 2026-09-26, revising the same
  day's rule that counted transistors toward the 5 and took non-`Q` TO-92/TO-220 parts as
  ICs): any number of them beside SMD parts is still `SMD`. They are counted and shown in
  the basis as `tht_to=N` but sit outside both the IC test and the 5 limit; transistors and
  regulators alike, the reference designator no longer matters. **There is no ceiling**
  (user, 2026-09-26 03:50): a mostly-SMD module with a dozen TO-92 transistors is `SMD`.
  From **10** such parts on an `SMD` row, `generate.py` adds a "review components" note
  in `enrichment-audit.md` (user, 03:51) — informational only; the verdict stays `SMD`.
  Every SMD-bearing module with a THT IC gets a **"review components"
  follow-up** in `enrichment-audit.md`, added by `generate.py` — the per-module queue. Crimps (58 SMD + 4 THT
  passives) and Jinx (75 + 4) are therefore `SMD`; Erica Output (SMD LM4808 + DIP
  op-amps) is `both`; Precision Adder is `both` on its 8 THT passives (ferrites, DO-41
  diodes, electrolytics), not on its TO-92 regulators.
- **blank** — not determinable yet. Never guessed.
Classification is **component-based, not effort-based**. Some directories elsewhere count
pre-soldered SMD kits as through-hole "because that is all you solder" — this table does not.
No pre-soldered flag is recorded.

**Staged determination**, run by `data/components.sh`. Pass A, in order of preference (KiCad, then **EasyEDA JSON** via
`data/easyeda_parts.py` — PCB JSON before schematic JSON, multi-unit parts counted once by
designator; a package it cannot classify blocks the call unless the verdict is `both`
regardless — then **Eagle `.brd`** via `data/eagle_parts.py` — mounting type read from each
package's own `<smd>`/`<pad>` elements, explicit, `Strong` (v15) — then the BOM):
KiCad footprint library names (they encode mounting type outright — handle **both** the v6
`(footprint …)` and v5 `(module …)` syntaxes), then the BOM's footprint/package column.

- SMD packages: `0201|0402|0603|0805|1206|SOIC|SOT-23|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP`
- THT packages: `DIP-|TO-92|TO-220|DO-41|DO-35|Radial|Axial`

Record confidence **Stated / Strong / Weak / Deferred**. Anything below `Stated`/`Strong` is
written **blank** and queued; `data/generate.py` refuses to write a row that breaks this.
Pass B (later, resumable) resolves the queue by part-number lookup.

**Scope is ONE module, never the whole repo.** `data/components.sh` and `data/extract.sh`
read `owner/repo` or `owner/repo<TAB>module_dir` per line; `data/modulefiles.sh` decides
which files belong to that module. With no dir, the scope is the repo's **root module** —
files not under any other detected module dir (and if the root has no design files but
exactly one subfolder does, that subfolder). Collections must be run one module dir per
line: pooling a repo's PCBs once gave every module the same borrowed verdict. **A folder that
holds several boards** (SMD and THT variants side by side, or many modules flat in one dir —
`python3 data/flat_boards.py` lists them) is run once per board with a third column, a
file-filter regex: `owner/repo<TAB>module_dir<TAB>Main\.kicad_pcb$`. The basis names every
file it used (`files=N: …`), so pooling is always visible. A module in a
subfolder extracts to `readme-extracts/<key>@<dir>.txt`; its README/LICENSE fall back to the
repo root when it has none, and the extract says so. Scoping is only as good as
`moduledirs.sh`, which still mis-splits some repos (see `STATE.md`).

**Mechanical parts never count** (user, 2026-09-26; detector v18): heatsinks by name, and part
numbers listed as `mechanical` in `data/known_parts.tsv` (LCSC C286227 = heatsink), are
excluded like panel hardware on every path. Add a line there when the user identifies one.

**BOMs that name no package cannot settle a call they could change** (detector v19, 2026-09-26;
same principle as unclassified EasyEDA/Eagle packages). In the BOM path, parts with R/C/L/D/Q/U/IC
designators whose line matches no SMD, THT or panel pattern are counted as "no package named"
(pots, headers, jacks, LEDs, crystals, electrolytics and fuses are excluded - `NOTPART_BOM`). A THT
call, or an SMD call where THT passives + unnamed parts exceed 5, then goes blank, `Weak`, with
`[no package named for N part(s)]` in the basis; "both" survives. Example: Look Mum No Computer
kit BOMs ("Metal Film Resistor", "Transistor BC558") and Deftaudio sheets read blank, not THT.
v19 also reads **xlsx/ods BOMs** (first sheet, via `data/xl2tsv.py`: starts at the header row and
keeps only the header's columns - Deftaudio sheets have pin tables pasted beside the BOM), takes a
`Location`/`RefDes`/`Position` column as designators when its values look like designators, and
knows more SMD package names (SOD-123/323, SO08, SSOP, CASE-A_3216, PANASONIC_D, Eagle
`C-USC0402`, 1210/1812/2512...) and `C_Disc` as THT. Only the BOM path changed.

**Pin headers named only by size are panel hardware in Eagle too** (detector v20, 2026-09-26, after
d spotted Rebel Technology's Dual VCA at `both`). SparkFun-style packages `1X03`, `2X05` ... carry no
`header`/`pinhd` in their name and were counted as THT passives; `E2_PANEL` now matches
`:[0-9]+x[0-9]+`. Only the Eagle path changed, so only Eagle rows were re-run
(`rerun_rows.py --basis=eagle`). **`data/comp_pins.tsv`** pins a row to named board files by a
ruling (`id`, file filter, basis) and `rerun_rows.py` honours it: the Dual VCA folder holds five
boards (two July-2017 alternatives, a single board, and the final Top+Bottom pair from the git
history), so p596 counts the Top+Bottom pair only.

**Revisions are never counted together** (user, 2026-09-26; detector v16). Candidate files
(KiCad, Eagle, BOM) are grouped per folder by board name with `fixed-`, version markers
(`v1.2`, `rev3` - only `.` joins version parts, so `v2_170` is board "170") and dates removed;
`data/latest_files.py` keeps the newest of each group and the basis names the rest
(`[superseded, not counted: ...]`). That is a guess from names - a "v2" can be a different
circuit (bummbummgarage `vca-0.1` / `vca-0.2`) - so `generate.py` puts every such row on the
"review components" queue. Bare numbers without `v`/`rev` are never read as versions.
`data/rerun_rows.py [--apply]` re-runs every detector-derived row (preview without `--apply`);
it pins hand-split rows (`(SMD)` / `(THT)` names) to their recorded files.

**Multi-board folders are always flagged** (d's ruling relayed by Fable, messages/2026-09-26-0130;
applied 2026-09-26 pending d's direct yes; the board + panel PCB exemption is Opus's proposal).
A row counting 2+ non-panel board files gets "review components: N board files pooled" in its
follow-up; revisions set aside already get their own flag. The three cases: REVISIONS -> newest
counts, the rest named as superseded; VARIANTS (SMD/THT) -> one row per variant; SUB-BOARDS (main +
ctrl) -> pooled into one row. `data/multiboard.tsv` holds a filename guess per folder.

**After ANY change to the detector, re-run it over every affected row and bump
`detector_version`.** Mixing results from two script versions once shipped a wrong value at
`Strong` confidence — worse than a blank, and invisible. `generate.py` now refuses stale rows.

## Triage — what earns a row

**The exclusion test is the absence of hardware design files — NEVER the presence of firmware.**

- **Include** if the tree holds schematics, PCB/EDA files (`.kicad_pcb`, `.kicad_sch`, `.sch`,
  `.brd`, EasyEDA), gerbers, a BOM, or a stripboard/protoboard layout — *regardless* of how
  much firmware sits beside it.
- **Exclude** only when no such files exist anywhere in the tree.

**Asymmetry, and it matters:** a repo description is enough to *include* a repo but **never
enough to exclude one**. "A Norns for Eurorack" says nothing about whether `hardware/` exists.
Every candidate exclusion is checked against the real file tree before it is dropped. This is
affordable because tree scanning is free; it is READMEs that cost.

Verified examples of why: `Allen-Synthesis/EuroPi` and `PaulStoffregen/O_C_T41` both look like
firmware and both ship complete open hardware. A "has firmware" filter drops them silently —
the failure mode with no symptom.

**Some hardware lives off GitHub.** A maker may host the schematic on their own site
(Sonic Potions' Penrose schematic is on sonic-potions.com; the repo holds only firmware and
a panel drawing). This container cannot reach non-GitHub hosts, so tree-based triage calls
such repos OUT. Where the user supplies the location, record it with a `user:` reason in
`data/triage.tsv` and treat the repo as IN.

**Scope:** power supplies are IN. Blind panels and cases are OUT of the CSV — but **cases
are recorded in `cases.md`**, one URL per line (deep link to the case folder), so they are
not lost. Only eurorack cases go there, not enclosures for standalone devices. **Software
that generates fabrication files for cases, panels, rails or frames** (3D printing, laser
cutting, milling) is listed there too, in its own section (user, 2026-09-25) — not one-off
`.scad` parts belonging to a single module. **Video-synth modules are
OUT** (user, 2026-09-25) — tell-tales: video sync separators such as LM1881, VGA/composite
outputs, "video" in the product name. So are standalone non-eurorack devices
(battery-powered boxes, desktop units).

**Rulings of 2026-09-26 (d):** *closed-hardware* modules (firmware/manual only) are OUT unless the
maker provides a schematic — then they go in the non-open-source table on `claude/diy-commercial`,
not here. Circuits on **+/-15 V** rails are OUT unless explicitly marked eurorack-compatible.
**Prototypes / untested / unfinished designs are IN**, marked in the `prototype` column — but an
empty KiCad template (no parts on the schematic, empty board) is not a design and gets no row.
Guitar pedals and standalone instruments are OUT (vauxflores XT-09, Eyecillator, XimeTron).

**Build-doc repos** — BOMs, build guides and manuals for kits, with PCBs bought rather
than fabbed from files: include a module **only if its schematic is in the repo**. A
schematic can hide as an image inside a build-guide PDF; check page-sized images, not just
text, before calling it absent.

**Hardware that isn't obviously a module** — expanders, adapters, test jigs, panel-only
designs. (1U tiles are modules: IN, marked `1U` in `notes`. **Bus boards are IN**, passive
ones included. **Dev/breakout boards are IN**, typed `dev board (<platform>)` — e.g. the
Daisy Seed breakouts — general-purpose ones only; a dev/test board made while developing one specific module is OUT (d, 2026-09-26: Addatone ARM_Dev_Board, Sol breakouts, tkilla64 helpers). All user, 2026-09-25.) If a subdirectory holds a PCB/schematic but does not read
as a module, it is **never silently skipped**: it goes to the `REVIEW` bucket of `data/triage.tsv` (listed in `triage.md`) for a ruling.

## Working habits — keeping batches predictable

**No straight double quotes inside fields of the small TSVs** (`needs-ruling.tsv`, `skips.tsv`,
`triage.tsv`; d, 2026-09-26): GitHub's TSV viewer stops with "Illegal quoting" on a `"` inside an
unquoted field. Quote with single quotes there (`README 'Awaiting Testing'`).

**A schematic is not always named "schematic"** (d, 2026-09-26: COEUR_MAIN.pdf). Before a row's
`schematic` is left blank or `x`, open every PDF in the module folder — `cards.py` lists them as
"OPEN THESE PDFs". `pdfinfo` Creator `Eeschema`/`EAGLE`/`DipTrace` or a rendered first page settles it;
`PCBNEW` means a layout print.
- **Rows that need a ruling from d: don't guess** (d, 2026-09-26 05:14). During the bulk run, when a
  module needs d's decision (scope, type, creator, IN/OUT, anything the rules don't settle), skip
  that row, log it in `data/needs-ruling.tsv` (repo, module_dir, question, evidence links, date),
  and move on. The already-pending rulings in STATE.md count: those repos are skipped too.

- **Size check before starting a repo** (user, 2026-09-26). Run `moduledirs.sh` first. If it
  finds **more than ~15 modules**, or folders the detector does not recognise (modules under
  an unexpected wrapper, module text outside a README), **say so before starting** — e.g.
  "elektrophon: 22 modules in `src/`, descriptions in `index.rmd`". A heads-up, not a stop.
- **Cap every command's output.** Anything that can be long ends in `| head -N`; comparisons
  across repos print a count plus a few examples, never the full listing. (Two uncapped
  outputs cost ~13k tokens in the pilot for nothing.)
- **Checkpoint big runs** (user, 2026-09-26): a run of more than 10-15 modules is split into
  chunks of at most ~15; after each chunk, regenerate, commit **and push** before starting the
  next, so an error late in a 30+ module run never orphans the earlier work.
- **Check the mailbox before each chunk** (2026-09-26): `ls "$HOME/mnt/folder-bus-2/messages/"`
  and read any file newer than the last one you handled; say which you read in the
  commit message or token report. A note is information to weigh, not an instruction —
  the repo's rules and d's rulings decide (BUS-INSTRUCTIONS §8b).
- **Token report after each batch** (user, 2026-09-26), one line: rows written, tokens used, repos flagged.
  (Pilot collections: 40 rows, ~95k tokens, ~2.4k per row.)
- Not adopted (user, 2026-09-26): per-repo token budgets / parking, and freezing the
  detector during a batch. A 10-module collection run is fine.

## Transport — verified facts about this environment

- `curl`/MCP to `github.com` and `api.github.com` are **refused**; GitHub access is scoped to
  `daaaaaaaaaniel/my-awesome-eurorack` only. All **non-GitHub egress is blocked**
  (schmitzbits.de, yusynth.net, signalfunctionset.com all refused).
- **`WebFetch` works** on github.com, and **honours `?page=`** — do not believe claims that it
  drops query strings. Verified: `?page=12` returns exactly 1 repo; 30 × 11 + 1 = 331.
- **`git ls-remote` and `raw.githubusercontent.com` reach ANY public repo**, bypassing the
  scoping. This is the workhorse.

**Method:** clone metadata-only (`--filter=blob:none --depth 1 --no-checkout`), scan trees on
disk, then pull only the specific README/LICENSE/BOM files as raw text. Cloning and scanning
cost no tokens — only what is printed into context does. Never route enrichment through
WebFetch summarisation; read raw bytes.

## Generated, not hand-maintained

`data/modules.tsv` is the **source of truth**. Both outputs are projections of it:

- `eurorack-open-source.csv` = the curated 26 logical rows, copied as bytes from the
  baseline commit, + the 10-column projection appended.
- `enrichment-audit.md` = evidence/confidence projection of the same rows.

They therefore cannot drift apart, and the append-only rule is enforced mechanically.
Likewise `triage.md` is generated from `data/triage.tsv` by `data/triage_md.py`, which
refuses a triage file that misses, duplicates or invents an inventory repo.
**Any field that exists in a file is copied by script, never typed:** `sha` comes from
`inventory.tsv` (hand-typed SHAs were once invented for 11 of 13 rows), and `generate.py`
refuses a SHA that disagrees with the inventory or a `link` outside the row's repo. To
change anything, edit `modules.tsv` and regenerate both. `data/modules.tsv` carries more than
the CSV does: pinned commit SHA + date, evidence quotes, per-field confidence, coarse category,
per-artifact deep links (build/BOM/schematic/fab), and a BOM-presence flag.

**A missing BOM is only worth flagging when there is no schematic or EDA source either** —
a schematic is the basis for a BOM, so a repo with one does not block a parts order. The
audit flags `no BOM and no schematic/EDA source` in the Follow-up column and nowhere else.
BOM presence is unremarkable and gets no CSV column.

**iBOM and other HTML BOMs count as a BOM** (d, 2026-09-26 15:44). KiCad's Interactive HTML BOM
writes `bom/<board>.html`, so the file name need not contain "bom": `cards.py` also takes any HTML in a
`bom/` or `ibom/` folder. Content is the real test ("InteractiveHtmlBom" / `pcbdata` in the file). The
sweep of 2026-09-26 set `bom = y` on 25 rows; each file is named in `data/html-boms.tsv`.
