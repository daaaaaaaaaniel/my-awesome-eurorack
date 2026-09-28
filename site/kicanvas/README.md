# KiCanvas (test, branch kicanvas-test; d 2026-09-28 02:15)

`kicanvas.js` is built from https://github.com/theacodes/kicanvas at commit b031159 (`npm ci && npm run build`),
MIT licence (LICENSE.md), with one local patch: `kicanvas-zoom-to-board.patch` - boards open fitted to their
Edge.Cuts outline instead of the drawing sheet (many boards sit off the sheet and opened empty).

Tested 2026-09-28 on 30 random KiCad rows: all 22 schematic sets render; KiCad 6-10 boards render; KiCad 4/5 boards
(file version 20171130 and older) draw tracks but no footprints, and 2 of them crash the parser - so `build.py` only
passes boards with version >= 20211014 (`data/kicad-versions.tsv`, read from each file's header by range request).
KiCanvas loads its fonts/icons from Google Fonts.

2026-09-28 03:16 (d): the page's own file list drives the viewer. Each file link shows that file in KiCanvas's main
pane via KiCanvas's "context-request" protocol + the public `Project.set_active_page()` (found by a Fable subagent;
no extra patch). The viewer opens on the first schematic (root sheet first). Files are HEAD-checked before loading:
one missing file (404) used to keep the whole viewer from loading; now it is struck out and the rest load.
Files with a duplicate basename are dropped (KiCanvas keys files by basename). Tested: Polivoks (3 sch + 3 pcb,
three separate sub-projects), Jinx (root + 4 sub-sheets: reference designators resolve), a forced 404.
