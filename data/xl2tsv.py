"""xlsx/ods (first sheet) -> TSV on stdout, for bom_parts.py. PROTOTYPE, not wired into components.sh (see STATE.md, Blank verdicts)."""
import re, sys, openpyxl, subprocess, os, tempfile, csv
p = sys.argv[1]
if p.lower().endswith(".ods"):
    d = tempfile.mkdtemp(); subprocess.run(["soffice","--headless","--convert-to","xlsx","--outdir",d,p],capture_output=True,timeout=60)
    p = os.path.join(d, os.path.splitext(os.path.basename(p))[0] + ".xlsx")
wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
ws = wb.worksheets[0]
w = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
rows = [["" if c is None else str(c).replace("\t", " ").replace("\n", " ").strip() for c in r]
        for r in ws.iter_rows(values_only=True)]
rows = [r for r in rows if any(r)]
# start at the header row (title rows above it hide the header from bom_parts.py) and keep only
# the header's columns: some sheets have unrelated tables pasted to the right (Deftaudio pin lists)
HW = re.compile(r"^(qty|quantity|qnty|count|anzahl|designators?|references?|refs?|location|part ?(number|no\.?)?|value|description|footprint|package)$", re.I)
hi = next((i for i, r in enumerate(rows[:15]) if sum(bool(HW.match(c)) for c in r) >= 2), 0)
hdr = rows[hi] if rows else []
last = max([j for j, c in enumerate(hdr) if c] or [len(hdr) - 1])
# a gap of 3+ empty header cells ends the table
for j in range(1, last + 1):
    if not any(hdr[j:j+3]) and j + 3 <= last: last = j - 1; break
try:
    for r in rows[hi:]:
        cells = r[:last + 1]
        if any(cells): w.writerow(cells)
except BrokenPipeError:
    pass
