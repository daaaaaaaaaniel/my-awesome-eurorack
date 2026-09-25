# STATE — where the work stands

Read this first when resuming. `CLAUDE.md` holds the rules; this file holds progress.
Update it whenever a phase finishes or a decision lands.

_Last updated: 2026-09-25, at commit after `a5e93ec`._

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
2. **Unrecoverable brand names.** When the maker's brand is not in the repo (`Voxmachina` ≠
   GitHub owner `musicdevghost`), use the GitHub owner and flag it, or leave `creator` blank?
3. **Triage rulings** — the 21 REVIEW repos in `triage.md`, plus "hardware but not a
   module" cases the pilot found but `data/triage.tsv` still marks `IN` (see
   *Known inconsistencies*).
4. **Jinx** (`kstammits/crimps/Jinx`) — its own module, or a revision of Crimps?
   And the curated `crimps` row reads `THT` where footprints say `both`: flagged, not edited
   (append-only rule).

## Next steps (mine)

- **Finish the pilot sample before the bulk run.** 18 of the 31 sampled repos have no row.
  Most are legitimate, but no collection has been expanded yet, so the step most likely to
  go wrong at scale is still untested:

  | status | repos |
  |---|---|
  | **collections, never expanded** | `BruteClaw/Analog-Synth` (60 dirs), `spielhuus/elektrophon` (44), `Thorinair/Avalon-Harmonics` (20), `ltrooney/diy-synth` (7), `kevinkewang/tiny_rack` (5), `AfterLaterAudio/Eurorack` (3), `jakplugg/Orgone-accumulator` (2) |
  | single modules, not yet written | `pingdynasty/Mix`, `joranvg/test-3` |
  | awaiting a ruling (decision 3) | `bpcmusic/TXb`, `WiggisModular/mmc`, `newdigate/teensy-eurorack`, `spherical-sound-society/vortex-generator` |
  | correctly no row | OUT: `glitched0xff/Midi2euroPiW`, `mortonkopf/Teensy-eurorack-rotating-step-divider`, `DatanoiseTV/PicoADK-Eurorack-Module`; REVIEW: `VoltageFoundryMod/ForgeSeries-CLK`, `samjkent/modular-mixer` |

  The user asked for collections to be capped at ~10 modules in the pilot.

- Then Phase 3 in batches: append to `data/modules.tsv`, run `data/generate.py`, commit per
  batch with its `data/` artifacts.

## Known inconsistencies

- `data/triage.tsv` marks these `IN`, but reading them in the pilot says otherwise:
  `WiggisModular/mmc` and `kevinkewang/tiny_rack` are cases (out of scope);
  `bpcmusic/TXb` is a bus board and `newdigate/teensy-eurorack` a Teensy shield
  (section 2); `spherical-sound-society/vortex-generator` says *"the hardware remains
  closed source, so please dont fabricate it"* — files present, but not buildable.
  Fix when decision 3 lands. The IN count (and so the ~1,504 projection) is inflated by
  cases like these.

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
