// BOM spreadsheets (d, 2026-09-28 17:51): SheetJS reads the file inside this worker, away from the page. Only plain
// cell text goes back (first maxRows x maxCols of every sheet).
importScripts("sheetjs/xlsx.full.min.js");
onmessage = (ev) => {
  try {
    const wb = XLSX.read(new Uint8Array(ev.data.buf), { type: "array", cellFormula: false, cellHTML: false, cellStyles: false, dense: true });
    const sheets = wb.SheetNames.map(n => {
      const rows = XLSX.utils.sheet_to_json(wb.Sheets[n], { header: 1, raw: false, defval: "", blankrows: false });
      return { name: String(n), rows: rows.slice(0, ev.data.maxRows).map(r => r.slice(0, ev.data.maxCols).map(c => String(c))) };
    });
    postMessage({ sheets });
  } catch (err) { postMessage({ error: String(err && err.message || err) }); }
};
