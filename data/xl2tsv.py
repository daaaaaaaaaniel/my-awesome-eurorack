"""xlsx/ods (first sheet) -> TSV on stdout, for bom_parts.py. PROTOTYPE, not wired into components.sh (see STATE.md, Blank verdicts)."""
import sys, openpyxl, subprocess, os, tempfile, csv
p = sys.argv[1]
if p.lower().endswith(".ods"):
    d = tempfile.mkdtemp(); subprocess.run(["soffice","--headless","--convert-to","xlsx","--outdir",d,p],capture_output=True,timeout=60)
    p = os.path.join(d, os.path.splitext(os.path.basename(p))[0] + ".xlsx")
wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
ws = wb.worksheets[0]
w = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
for row in ws.iter_rows(values_only=True):
    cells = ["" if c is None else str(c).replace("\t"," ").replace("\n"," ") for c in row]
    if any(x.strip() for x in cells): w.writerow(cells)
