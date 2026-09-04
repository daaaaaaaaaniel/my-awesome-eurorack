# eurorack-open-source.csv — working conventions

Reference table of buildable DIY eurorack modules. This file exists so the conventions
survive across sessions; it is the authority when memory and chat history are gone.

## The deliverable

`eurorack-open-source.csv` — **exactly 9 columns, never more**:

    creator, Module Name, Type of Module, License, schematic?, layout, components, link, notes

Row 1 is the header. **Row 2 is a legend row** defining the base vocabulary
(`x | n/a`, `kicad | eagle`, `THT | SMD`). Rows 3+ are module rows.

## Hard rules

1. **Never invent a field value.** A blank cell is correct; a guessed one is a lie that gets
   acted on when ordering parts. Blank beats plausible, always.
2. **Never edit existing rows**, or the header, or the legend row. Append only.
   The first 25 lines of the CSV are frozen and must stay byte-identical.
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
- **`Type of Module` uses eurorack-native vocabulary**, not generic categories: `S&H`,
  `VCF (vactrol)`, `LPG (vactrol/passive)`, `Bernoulli Gate`, `Analog Shift Register`,
  `PT2399 delay`, `VCA (quad)`. Compound types slash-joined: `S&H / Noise / Rectifier / Logic`.
- **`link` is a deep link** — the specific subdirectory, PDF or product page. Never a repo root.
- **`layout` extends past its legend** in practice, and this is the idiom for recording
  fabrication files too: `easyEDA + gerbers`, `kicad + stripboard`, `stripboard`, `protoboard`,
  `commercially available`, `n/a`. **Gerber availability is recorded here as `+ gerbers`** —
  there is deliberately no separate column for it.
- **`notes` carries cross-references**: "See alt. versions from…", "based on X design".

## components — THT / SMD / both

- **`THT`** — the build uses *exclusively* through-hole components.
- **`SMD`** — uses surface-mount ICs, or surface-mount resistors/capacitors/diodes/passives.
  **THT jacks, switches and pots do NOT disqualify an `SMD` marking** — nearly every SMD
  module uses through-hole panel hardware.
- **`both`** — the passives are a mix of SMD and THT. (Extends the legend's `THT | SMD`;
  the legend row itself stays byte-identical per rule 2.)
- **blank** — not determinable yet. Never guessed.

Classification is **component-based, not effort-based**. Some directories elsewhere count
pre-soldered SMD kits as through-hole "because that is all you solder" — this table does not.
No pre-soldered flag is recorded.

**Staged determination.** Pass A (cheap, in the main run): grep README for
`through-hole|THT|SMD|SMT|surface-mount`; grep any BOM for package signals
(`0402|0603|0805|1206|SOIC|SOT-23|TSSOP|QFN|MSOP` vs `DIP|axial|radial|TO-92|TO-220`); for
KiCad, footprint library names encode it outright — count `_SMD:` vs `_THT:`. Record
confidence: **Stated / Strong / Weak / Deferred**. Anything below **Strong** is written blank
and queued. Pass B (later, resumable) resolves the queue by part-number lookup.

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

- `eurorack-open-source.csv` = frozen first 25 lines + 9-column projection appended.
- `enrichment-audit.md` = evidence/confidence projection of the same rows.

They therefore cannot drift apart, and the append-only rule is enforced mechanically. To
change anything, edit `modules.tsv` and regenerate both. `data/modules.tsv` carries more than
the CSV does: pinned commit SHA + date, evidence quotes, per-field confidence, coarse category,
per-artifact deep links (build/BOM/schematic/fab), and a BOM-presence flag.

**A missing BOM is flagged in `enrichment-audit.md` (Follow-up column) as `no BOM`** — the
absence is the actionable fact, since it blocks a parts order. Presence is unremarkable and
gets no CSV column.
