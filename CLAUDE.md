# eurorack-open-source.csv — working conventions

Reference table of buildable DIY eurorack modules. This file exists so the conventions
survive across sessions; it is the authority when memory and chat history are gone.

**Progress, open decisions and how to resume live in `STATE.md` — read it first.**

## The deliverable

`eurorack-open-source.csv` — **exactly 9 columns, never more**:

    creator, Module Name, Type of Module, License, schematic?, layout, components, link, notes

Row 1 is the header. **Row 2 is a legend row** defining the base vocabulary
(`x | n/a`, `kicad | eagle`, `THT | SMD`). Rows 3+ are module rows.

## Hard rules

1. **Never invent a field value.** A blank cell is correct; a guessed one is a lie that gets
   acted on when ordering parts. Blank beats plausible, always.
2. **Never edit existing rows**, or the header, or the legend row. Append only.
   The curated prefix is **26 logical CSV rows** — which span **27 physical lines**,
   because one `creator` field contains an embedded newline and the file has no trailing
   newline. **Never slice it by line count**: `head -26` cuts into the last curated row.
   `data/generate.py` copies the baseline commit's bytes instead, which is what makes
   append-only mechanical rather than a thing to remember.
3. **Preserve exact column order**, and keep the column count at 9.
4. Every non-blank cell must be traceable to a file path in the repo tree or a quoted line
   of raw text. If neither exists, the cell is blank.

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
- **Repos outside the star list** may be added when the user asks (e.g. the Forge repos).
  They go into `data/inventory.tsv` with `page = user-added`, so SHA and link checks work.
- **`Type of Module` must state a function.** Never `eurorack module`, `module` or
  `synth module` — everything in this table is a eurorack module, so it says nothing.
- **`Type of Module` uses eurorack-native vocabulary**, not generic categories: `S&H`,
  `VCF (vactrol)`, `LPG (vactrol/passive)`, `Bernoulli Gate`, `Analog Shift Register`,
  `PT2399 delay`, `VCA (quad)`. Compound types slash-joined: `S&H / Noise / Rectifier / Logic`.
- **`link` is a deep link** — the specific subdirectory, PDF or product page. Never a repo root.
- **`layout` extends past its legend** in practice, and this is the idiom for recording
  fabrication files too: `easyEDA + gerbers`, `kicad + stripboard`, `stripboard`, `protoboard`,
  `commercially available`, `n/a`. **Gerber availability is recorded here as `+ gerbers`** —
  there is deliberately no separate column for it.
- **`notes` carries cross-references only**: "See alt. versions from…", "based on X design",
  and lineage with **more than one ancestor** (vca-8 draws on YuSynth *and* Kassutronics, so
  `creator` stays `Polykit` and both sources go here — `creator` keeps its
  `original + this version` shape). Not board names, licence detail, or repo trivia.
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
- **`both`** — the passives are a mix of SMD and THT. (Extends the legend's `THT | SMD`;
  the legend row itself stays byte-identical per rule 2.)
- **The 3-part threshold:** after excluding panel hardware, a build with SMD parts and
  **3 or fewer THT parts is still `SMD`**. Four or more mixed THT passives make it `both`.
- **blank** — not determinable yet. Never guessed.

Classification is **component-based, not effort-based**. Some directories elsewhere count
pre-soldered SMD kits as through-hole "because that is all you solder" — this table does not.
No pre-soldered flag is recorded.

**Staged determination**, run by `data/components.sh`. Pass A, in order of preference:
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
line: pooling a repo's PCBs once gave every module the same borrowed verdict. A module in a
subfolder extracts to `readme-extracts/<key>@<dir>.txt`; its README/LICENSE fall back to the
repo root when it has none, and the extract says so. Scoping is only as good as
`moduledirs.sh`, which still mis-splits some repos (see `STATE.md`).

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

**Build-doc repos** — BOMs, build guides and manuals for kits, with PCBs bought rather
than fabbed from files: include a module **only if its schematic is in the repo**. A
schematic can hide as an image inside a build-guide PDF; check page-sized images, not just
text, before calling it absent.

**Hardware that isn't obviously a module** — breakouts, expanders, adapters, test jigs,
panel-only designs. (1U tiles are modules: IN, marked `1U` in `notes`. **Bus boards are IN**,
passive ones included — user, 2026-09-25.) If a subdirectory holds a PCB/schematic but does not read
as a module, it is **never silently skipped**: it goes to `triage.md` section 2 for a ruling.

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
  baseline commit, + the 9-column projection appended.
- `enrichment-audit.md` = evidence/confidence projection of the same rows.

They therefore cannot drift apart, and the append-only rule is enforced mechanically.
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
