# SheetJS (xlsx.full.min.js) for the BOM box

`xlsx.full.min.js` is SheetJS Community Edition **0.18.5** from npm (`npm pack xlsx@0.18.5`), Apache-2.0 (LICENSE here).
The module pages use it to show XLSX / XLS / ODS BOMs (d, 2026-09-28 17:51). It is kept in the repo, like KiCanvas, so
the site keeps working without anyone maintaining it.

0.18.5 is the last release on npm; newer releases are only on cdn.sheetjs.com, which the build environment could not
reach. Two advisories apply to 0.18.5 when reading untrusted files (prototype pollution, CVE-2023-30533; a slow regular
expression, CVE-2024-22363). The site therefore runs SheetJS only inside a Web Worker (`bom-sheet.js`): it gets the file
bytes and returns plain cell text, so a crafted file cannot reach the page, and the worker is stopped after 20 s.
To upgrade: replace this file with a newer `xlsx.full.min.js` (e.g. https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/)
and run `site/bomtest/bom.test.js` on a few spreadsheet BOMs.
