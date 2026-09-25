# Pre-flight review of the bulk run — 2026-09-26

Written by a separate (Fable) session before the overnight Phase 3 run, on branch
`audit/fable-preflight`, rebased onto `fc6e6e5`. Not to be confused with
`enrichment-audit.md`, which is the generated per-row evidence table.

Confidence markers as in `BUS-INSTRUCTIONS.md`: `[M]` measured here · `[I]` inferred.

## What was verified before anything was changed `[M]`

- `python3 data/generate.py` and `data/triage_md.py` reproduce the committed files byte for
  byte on `d5b3c9f` (clean `git diff`).
- All mechanically-derived rows in `modules.tsv` satisfy the SMD/THT rule when the verdict
  is re-derived from the recorded tally (46 rows at `d5b3c9f`, 87 at `fc6e6e5`).
- No duplicate ids or duplicate (repo, module_dir, module_name) rows. Dates agree with the
  inventory at month level.
- `raw.githubusercontent.com/<owner>/<repo>/<7-char sha>/<path>` works (same bytes as the
  branch fetch), so evidence can be pinned.
- A missing path on raw.githubusercontent returns HTTP 404 with the body `404: Not Found`.

## Findings, ranked

### 1. Flat folders holding several boards are invisible to `moduledirs.sh` — and get pooled

`moduledirs.sh` splits modules by *directory*. When several boards sit side by side in one
folder, they are one "module" and `components.sh` pools every board into one verdict — the
failure `CLAUDE.md` records as already paid for once, now at file level instead of folder
level. `[M]`:

- `GroundGrown/eurorack-modules`: 72 Eagle `.brd` (≈39 distinct modules × main/ctrl/rev)
  flat in the repo root → detected as **1** module dir. No `.kicad_pcb`, so the BOM path
  would have read the first two BOM files (alphabetical) at `Stated` confidence.
- `ThisIsNotRocketScience/Eurorack-Modules`: `Development/Eurorack Set 9` holds 20 Eagle
  projects flat; the "Set N" folders are containers, not modules.
- `Thorinair/Avalon-Harmonics` `CVMod8_V2` and `VU`: SMD and THT boards in one `kicad/`
  folder. The committed rows are correct only because they were split by hand; re-running
  the detector on the dir gives `both` for all of them.
- Overall: **307 of 1,436** todo/done module dirs hold more than one non-panel board file,
  across 102 repos (`python3 data/flat_boards.py`). Many are legitimately one module on
  main + control boards; the ones to split are distinct modules and `_SMD`/`_THT` or
  `rev1`/`rev2` variants.
- Consequence: the "1,468 module dirs (upper bound)" in `triage.md` is not an upper bound.

**On the branch:** `components.sh` takes an optional third input column, a file filter
(`owner/repo<TAB>module_dir<TAB>regex`), and names every file that contributed
(`files=N: a, b`) so pooling is visible in the basis. `data/flat_boards.py` lists the
candidates. With the filter, the three Avalon rows reproduce from the script `[M]`.

### 2. Evidence is fetched at the branch tip, not at the pinned SHA

`components.sh`, `extract.sh` and `clone_all.sh` all read the *current* default branch,
while the row records `inventory.tsv`'s `head_sha` and `generate.py` enforces that the two
match. Nothing enforces that the evidence came from that commit. `[M]` one day after the
harvest, **12 of 346 repos have already moved past their pin** (`git ls-remote`):
Allen-Synthesis/EuroPi, Deftaudio/Midi-boards, nanassound/eurorack-nanassound,
benjiaomodular/EuroPanelMaker, tpcarlson/synth-diy, TomWhitwell/Workshop_Computer
(already has a row), dchwebb/Retrospector, shorepine/tulipcc, cob333/Pico-Eurorack,
cob333/PicoPro-Eurorack, diyelectromusic/sdemp_pcbs, ghostintranslation/drone.
`triglav-modular/Voltage_Processor` is now **unreachable** (deleted or private); its tree
is committed but every fetch for it will fail.

**On the branch:** both scripts fetch at `head_sha` (branch tip only as fallback);
`extract.sh` records it in the header. Trees in `data/trees/` were taken at whatever HEAD
was at clone time — for the 12 drifted repos they may not match the pin; `clone_all.sh`
should compare `git rev-parse --short HEAD` with the inventory and log DRIFT.

### 3. Fetch failures are reported as absence of files

`components.sh` called `curl` without `--fail`, so a 404 body was parsed as a BOM (empty
tally → Deferred with a misleading basis) and a failed `.kicad_pcb` fetch silently fell
through to the BOM path — a *different confidence* from a transient error. With no source
found, the basis read "no .kicad_pcb and no machine-readable BOM in scope", which is false
when the files exist but the network failed. Over an overnight run of ~1,300 dirs this is
the most likely way to ship wrong blanks with a wrong reason. Paths were also only
space-encoded (`#`, `&`, `+`, `%` in a filename would break the URL).

**On the branch:** `--fail`, full URL-encoding, and explicit outcomes: `fetch failed for N
file(s) at <sha> - re-run, do not read as absence`; `N .kicad_pcb fetched but held no
footprints (LFS stub or empty board?)`; a `; fetch failed for N other file(s)` note on
partial results. `extract.sh` writes `(… fetch FAILED …)` markers into the extract.

### 4. Silent `head -4` / `head -2` caps

Only the first 4 `.kicad_pcb` and first 2 BOM files (tree order) were read, and the basis
named only the *last* file, so neither truncation nor pooling was visible. `[M]` removing
the caps changes no verdict on the existing rows; two tiny_rack tallies grow because all
BOMs are now read. Removed; every file used is listed.

### 5. BOM-path regex gaps (the path used for every non-KiCad module; 62 IN repos are Eagle)

`[M]` with synthetic lines:
- `DIP8`, `DIP 8`, `DIL8`, `TO92` were **not** recognised as THT ICs (only `DIP-`/`TO-92`),
  so an SMD board with DIP op-amps in the BOM read `SMD` instead of `both`, at `Stated`.
- Chip sizes matched inside part numbers: `C120641` (an LCSC code) counted as `1206`.
- LEDs, pots and trimmers were excluded on the KiCad path but **counted as THT passives on
  the BOM path**, so the 5-passive cap was applied inconsistently between sources.
- `bom_parts.py` treated a `Part` column as designators; when it holds descriptions
  ("Resistor 10k 1/4W") every line's quantity became its word count.

**On the branch:** BOM-specific regexes (`THT_IC_BOM`, `SMD_BOM` with stand-alone sizes,
`PANEL_BOM`), and `Part` is a designator column only when its values look like designators.

### 6. `generate.py` guards that were missing

Added: duplicate id / duplicate (repo, module_dir, module_name); `components` vocabulary;
**verdict re-derived from the recorded tally** (a hand-edited call can no longer disagree
with its evidence); `date` vs inventory month. All current rows pass `[M]`.

### 7. Cost shape of the run `[M]`

- 309 IN repos → 1,436 module dirs; **174 repos are single-module, 18 repos hold 693 dirs
  (48%)**: diyelectromusic/sdemp_pcbs 68 (mostly Arduino/Pi boards, not eurorack),
  RebelTechnology 62 (pedals, OWL, adapters mixed in), BruteClaw 60, elektrophon 57 (incl.
  `content/old/`), ThisIsNotRocketScience 54 (mis-split), bummbummgarage 41, …
- Network is not the bottleneck: ~0.5 s per module for `components.sh`, ~1 s for
  `extract.sh` → the whole todo list is ~40 min serial, ~10 min with 4 workers.
- `extract.sh` fetched the README **three times** per module; now once.
- Extracts are ~1.6 KB median, 6 KB p90; at ~2.4k tokens/row (CLAUDE.md's pilot figure) the
  remaining ~1,300 dirs are of the order of 3M+ tokens. The token cost is in reading and
  typing rows, not in fetching.

### 8. Smaller items (not changed)

- Three copies of the "hardware file" regex (`classify.sh`, `moduledirs.sh`,
  `modulefiles.sh`) differ: `.dip`/`.diy`/`.pcb` are in one but not another, and `.dch`
  (DipTrace schematic, noted in STATE.md) is in none. One shared definition would end drift.
- `moduledirs.sh`'s `norm()` strips leading digits, so its `3d` part-name can never match.
- `generate.py`'s `has_source` treats `n/a` as a source (truthy string); harmless today.
- Eagle `.brd` is XML with `<smd>` vs `<pad>` per package — a mechanical, reliable
  SMD/THT source for the 62 Eagle repos (297 dirs) that currently fall to the BOM path.
  `.xlsx` BOMs (pingdynasty, AfterLaterAudio) could be read with `zipfile` + XML, no deps.
- `BUS-INSTRUCTIONS.md` §10 asks whether the VM home survives a session: `[M]` it does not
  need to — each session gets its own `/sessions/rcw-<id>/`, so the askpass helper is
  per-session by construction.

## Structures for an unattended overnight run

Everything below is on the branch; nothing has been run over the full list yet.

- **`data/runlist.tsv`** (`python3 data/runlist.py`, idempotent) — one line per
  (repo, module_dir) of every IN repo, tiered: 1 = single-module repos first (186), 2 =
  2–5 dirs (220), 3 = 6–20 (337), 4 = >20 (693, do last, per repo with the size heads-up).
  `status` is derived from `modules.tsv` (a row at module level covers its per-board
  sub-dirs); `boards` > 1 flags dirs to check with `flat_boards.py` before writing rows.
- **`data/prefetch.sh [tiers]`** — runs `components.sh` → `data/components-out.tsv` and
  `extract.sh` → `data/readme-extracts/` over every `todo` line, 4 workers, resumable
  (skips what exists, retries `fetch failed`). Run it *before* the token-expensive part so
  the session reads only local files, sees no network errors mid-batch, and all evidence
  is at the pinned SHAs. Commit its outputs as a batch of their own.
- **Resumability** is the real requirement for a run that outlives one context: commit and
  push per chunk (already in CLAUDE.md), and keep `STATE.md`'s "next" line pointing at a
  tier/repo in `runlist.tsv` rather than at memory.
- **Plumbing** (BUS-INSTRUCTIONS): the Mac must stay awake with the image mounted and the
  app open all night — `caffeinate -dims` in a terminal is the cheap insurance. Every new
  session needs the folder grant and the delete-permission prompt again.

## Adopting this branch

- The detector is **v14** (Opus's v13 EasyEDA path + the fixes above). Regression `[M]`:
  over all 87 tally rows at `fc6e6e5`, no verdict or confidence changes except the three
  hand-split Avalon rows, which need the file-filter column to reproduce. So relabelling
  existing rows 13 → 14 is mechanical; add a filter for p60/p61/p84/p85 style rows.
- `generate.py` will refuse `modules.tsv` until rows carry `14` — by the repo's own rule.
- If Opus has uncommitted detector edits, take these as a diff (`git diff fc6e6e5
  audit/fable-preflight -- data/`) rather than a merge.
