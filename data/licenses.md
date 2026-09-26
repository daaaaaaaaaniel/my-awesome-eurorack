# Licences — how the site categorises the `license` column

`data/license-map.tsv` maps every distinct value of the `license` column in
`data/modules.tsv` to one or more **grants**. It changes nothing in
`modules.tsv` or the CSV; the raw string and its `license_basis` quote stay
on every module page.

**Ruling (d, 2026-09-26 13:37): a module can carry several licences**, e.g. one
for hardware and one for firmware. The unit is therefore a grant =
(licence family, version, scope), and a raw string like
`CC BY-SA 3.0 (hardware) / MIT (STM32 code) / GPL v3 (AVR code)` is three rows.

## Columns

| column | meaning |
|---|---|
| `license` | the exact raw string (the empty string is a row too) |
| `rows` | how many `modules.tsv` rows carry it |
| `seq` | position in the ` / ` list, 1-based |
| `family` | version-free licence family — the value the site's **Licence** filter uses |
| `version` | **only when the raw string states it**; `CC BY-SA` and `GPL` stay unversioned |
| `scope_raw` | the parenthetical, verbatim, when it names a scope |
| `scope` | `hardware` · `software` · `panel` · `hardware+software` · `unstated` |
| `terms` | a property of the *family* (below) — the site's **Terms** filter |
| `status` | `draft` = parser proposal · `ok` = d confirmed · `UNMAPPED` |
| `note` | a qualifier that is not a scope (`free for DIY; contact the author before retail`), or scope text that needed interpreting |

Draft produced by `data/license_map_draft.py --write`, which **overwrites the
file**; once rows are `ok`, edit the TSV instead of re-running.

## Families

`MIT` `Apache` `BSD` `CC-BY` `CC-BY-SA` `CC-BY-NC` `CC-BY-NC-SA` `CC0` `GPL`
`CERN-OHL-P` `CERN-OHL-S` `CERN-OHL-W` `custom` `none-named` `none-found` `not-open` `unclear`

## Terms vocabulary

| terms | families | what it says |
|---|---|---|
| `permissive` | MIT, Apache, BSD, CC-BY, CERN-OHL-P | attribution-style licence |
| `copyleft` | GPL, CC-BY-SA, CERN-OHL-S, CERN-OHL-W | share-alike / reciprocal |
| `non-commercial` | CC-BY-NC, CC-BY-NC-SA | licence forbids commercial use |
| `public-domain` | CC0 | |
| `custom` | custom | the repo's own terms; the raw text is on the page, we don't classify it further |
| `none-named` | none-named | the repo *says* open source but names no licence |
| `none-found` | none-found (blank cell) | **no LICENSE file or README statement was found in the files checked** — not the same as the repo saying there is none |
| `not-open` | not-open | proprietary / closed source / "none granted" / "not open source", as the repo states |
| `unclear` | unclear | the statement doesn't pick (e.g. "Creative Commons or MIT") |

## Rules that keep it honest

1. **Never infer a version.** 40 rows say `CC BY-SA` and 8 say `GPL`; they stay unversioned. SPDX ids that encode `-only` / `-or-later` are not used because the data doesn't say.
2. **Blank is "none found", never "no licence".** `license_basis` records what was checked (typically "no LICENSE file, no README statement"). A licence may exist somewhere we didn't look.
3. **`none-named` ≠ `none-found`.** The first is a claim the repo makes; the second is our absence of evidence.
4. **`custom` is not non-commercial and not permissive.** "Free for DIY; contact the author before retail" is a custom term; it's shown verbatim.
5. **Terms describe the family, not the module.** "Permissive" is true of MIT; whether a given repo's schematic PDF is actually covered by its root LICENSE is not something the table can see. The site says so.
6. **Scope `unstated` is shown as "whole repository (scope not stated)"**, never silently as hardware or software.
7. **Multi-valued filters.** A module with three grants appears under all three families. The card chip shows the scope when stated (`MIT · sw`), so a hit under `MIT` whose hardware is `CC BY-SA · hw` is visibly that.
8. **No "open source: yes/no" boolean.** It would need a definition (OSI/OSHWA-approved?) that excludes NC and custom licences and would be argued about; the Terms filter carries the same information without the label.

## Parser interpretations worth a glance when reviewing

- `(PCB/panel)`, `(PCBs, panel)`, `(BOM, schematic)`, `(DSP MCU board)` → scope `hardware`.
- `(board files, firmware - per README)` → `hardware+software`.
- `(hardware, OSHWA UK000005)`, `(hardware, per README)` → `hardware`; the extra text is in `note`.
- `Creative Commons or MIT (software)` → family `unclear`, terms `unclear` (row status `draft`, not `UNMAPPED`, because that *is* the right answer).
