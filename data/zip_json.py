#!/usr/bin/env python3
"""zip_json.py ZIP OUTDIR - extract every .json member of ZIP into OUTDIR (paths kept), and the .json members
of zips nested one level inside it into OUTDIR/<inner zip name without .zip>/. For components.sh's zipped
EasyEDA exports (v26); stdlib only, so it behaves the same on macOS and Linux."""
import io, os, sys, zipfile
def out(d, name, data):
    p = os.path.normpath(os.path.join(d, name))
    if not p.startswith(os.path.normpath(d) + os.sep): return          # no ../ escapes
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
def walk(z, d, depth):
    for n in z.namelist():
        low = n.lower()
        if low.endswith(".json"): out(d, n, z.read(n))
        elif low.endswith(".zip") and depth == 0:
            try: walk(zipfile.ZipFile(io.BytesIO(z.read(n))), os.path.join(d, n[:-4]), 1)
            except zipfile.BadZipFile: pass
try: walk(zipfile.ZipFile(sys.argv[1]), sys.argv[2], 0)
except zipfile.BadZipFile: sys.exit(1)
