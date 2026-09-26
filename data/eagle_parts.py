#!/usr/bin/env python3
"""Read an Eagle (v6+, XML) .brd on stdin; print one line per placed part:
<library>:<package>\t<reference>\t<smd|tht|none>

Mounting type is EXPLICIT in Eagle: a package is drawn from <smd> pads or <pad> (drilled)
elements, so no library-name heuristics are needed. A package with both (an SMD connector
with through-hole shield tabs, say) is reported as smd - a genuinely through-hole part
never carries an <smd> element. Packages with neither (logos, holes, fiducials) are "none".

Pre-v6 binary .brd files are not XML: nothing is printed and the caller falls through.
"""
import sys
import xml.etree.ElementTree as ET

raw = sys.stdin.buffer.read()
if not raw.lstrip().startswith(b"<?xml") and b"<eagle" not in raw[:2000]:
    sys.exit()
try:
    root = ET.fromstring(raw)
except ET.ParseError:
    sys.exit()
kind = {}
for lib in root.iter("library"):
    lname = lib.get("name", "")
    for pk in lib.iter("package"):
        n_smd = len(pk.findall("smd")); n_pad = len(pk.findall("pad"))
        kind[(lname, pk.get("name", ""))] = "smd" if n_smd else ("tht" if n_pad else "none")
for el in root.iter("element"):
    lib, pkg, ref = el.get("library", ""), el.get("package", ""), el.get("name", "")
    k = kind.get((lib, pkg))
    if k is None:   # package defined under another library name (library_urn variants)
        k = next((v for (l, p), v in kind.items() if p == pkg), "none")
    print(f"{lib}:{pkg}\t{ref}\t{k}")
