# KiCanvas (test, branch kicanvas-test; d 2026-09-28 02:15)

`kicanvas.js` is built from https://github.com/theacodes/kicanvas at commit b031159 (`npm ci && npm run build`),
MIT licence (LICENSE.md), with one local patch: `kicanvas-zoom-to-board.patch` - boards open fitted to their
Edge.Cuts outline instead of the drawing sheet (many boards sit off the sheet and opened empty).

Tested 2026-09-28 on 30 random KiCad rows: all 22 schematic sets render; KiCad 6-10 boards render; KiCad 4/5 boards
(file version 20171130 and older) draw tracks but no footprints, and 2 of them crash the parser - so `build.py` only
passes boards with version >= 20211014 (`data/kicad-versions.tsv`, read from each file's header by range request).
KiCanvas loads its fonts/icons from Google Fonts.
