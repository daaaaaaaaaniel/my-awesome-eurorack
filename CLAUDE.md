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
- **`creator` carries lineage**: original designer `+` whoever made this version —
  `Rene Schmitz + Divergent Waves`, `YuSynth + thismatters`, `Mutable Instruments + Karltron`.
  Derived modules get `(modified)` appended in `Module Name`: `YASH (modified)`.
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
- **Multi-licence repos record the full split in `License`**, e.g.
  `CERN-OHL-P v2 (hardware) / CC BY-SA 4.0 (panel) / MIT (firmware)`. Never in `notes`.
- **Lineage is often at the END of a README**, in a `# References` / `# Credits` section as
  bare URLs rather than prose. `data/extract.sh` greps for those headings and for known
  designer domains; do not rely on "based on" appearing in the text.

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

**Scope:** power supplies are IN. Blind panels and cases are OUT.

**Hardware that isn't obviously a module** — bus boards, breakouts, expanders, adapters, test
jigs, 1U tiles, panel-only designs. If a subdirectory holds a PCB/schematic but does not read
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

They therefore cannot drift apart, and the append-only rule is enforced mechanically. To
change anything, edit `modules.tsv` and regenerate both. `data/modules.tsv` carries more than
the CSV does: pinned commit SHA + date, evidence quotes, per-field confidence, coarse category,
per-artifact deep links (build/BOM/schematic/fab), and a BOM-presence flag.

**A missing BOM is only worth flagging when there is no schematic or EDA source either** —
a schematic is the basis for a BOM, so a repo with one does not block a parts order. The
audit flags `no BOM and no schematic/EDA source` in the Follow-up column and nowhere else.
BOM presence is unremarkable and gets no CSV column.
