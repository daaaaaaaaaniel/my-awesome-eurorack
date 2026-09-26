#!/usr/bin/env python3
"""Read a KiCad/Eagle Interactive HTML BOM (iBOM) on stdin; print one line per placed part:
<footprint name><TAB><reference><TAB><smd|tht|none>

Mounting type is EXPLICIT in iBOM: every pad carries "type": "smd" or "th", so, as with Eagle
(eagle_parts.py), no name heuristics decide it. A part with any SMD pad is smd (an SMD part
with through-hole tabs); all-th is tht; no pads is none. Parts iBOM left off its BOM table
(bom.skipped: logos, holes, blacklisted or DNP parts) are not printed. The footprint name
comes from the BOM table's fields (new format) or its rows (old format); "" if absent.

pcbdata is stored either as plain JSON or LZ-String compressed (decompressFromBase64).
Not an iBOM: nothing is printed and the caller falls through.
"""
import json, re, sys

B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

def lz_b64(s):
    """port of LZString.decompressFromBase64"""
    rev = {c: i for i, c in enumerate(B64)}
    n = len(s)
    get = lambda i: rev.get(s[i], 0) if i < n else 0
    reset = 32
    st = {"val": get(0), "pos": reset, "idx": 1}
    def bits(k):
        b, p, mx = 0, 1, 1 << k
        while p != mx:
            r = st["val"] & st["pos"]; st["pos"] >>= 1
            if st["pos"] == 0:
                st["pos"] = reset; st["val"] = get(st["idx"]); st["idx"] += 1
            if r: b |= p
            p <<= 1
        return b
    d = {0: 0, 1: 1, 2: 2}; enl, size, nb = 4, 4, 3
    t = bits(2)
    if t == 2: return ""
    c = chr(bits(8 if t == 0 else 16))
    d[3] = c; w = c; out = [c]
    while True:
        if st["idx"] > n: return ""
        c = bits(nb)
        if c in (0, 1):
            d[size] = chr(bits(8 if c == 0 else 16)); size += 1; c = size - 1; enl -= 1
        elif c == 2:
            return "".join(out).encode("utf-16", "surrogatepass").decode("utf-16")
        if enl == 0: enl = 1 << nb; nb += 1
        if c in d: e = d[c]
        elif c == size: e = w + w[0]
        else: return None
        out.append(e); d[size] = w + e[0]; size += 1; enl -= 1; w = e
        if enl == 0: enl = 1 << nb; nb += 1

raw = sys.stdin.read()
if "pcbdata" not in raw:
    sys.exit()
m = re.search(r'pcbdata\s*=\s*JSON\.parse\(\s*LZString\.decompressFromBase64\(\s*"([^"]+)"', raw)
try:
    if m:
        pcb = json.loads(lz_b64(m.group(1)))
    else:
        m = re.search(r"var\s+pcbdata\s*=\s*", raw)
        if not m: sys.exit()
        pcb, _ = json.JSONDecoder().raw_decode(raw[m.end():])
except Exception as e:
    print(f"ibom_parts.py: cannot decode pcbdata ({e})", file=sys.stderr); sys.exit()

fps = pcb.get("footprints") or pcb.get("modules") or []
bom = pcb.get("bom") or {}
name = {}
skipped = set(bom.get("skipped") or [])
fields = bom.get("fields") or {}
for fid, fv in fields.items():                      # new format: {id: [value, footprint, ...]}
    if isinstance(fv, list) and len(fv) > 1 and fv[1]: name[int(fid)] = str(fv[1])
    elif isinstance(fv, list) and fv: name[int(fid)] = "value:" + str(fv[0])   # no footprint field: the value still names LEDs, jacks...
for grp in bom.get("both") or []:                   # old format rows: [qty, value, footprint, [[ref, id]...]]
    if grp and not isinstance(grp[0], list) and len(grp) > 3:
        for ref_id in grp[3]:
            if isinstance(ref_id, list) and len(ref_id) > 1: name.setdefault(int(ref_id[1]), str(grp[2]))
for i, f in enumerate(fps):
    if i in skipped: continue
    types = {p.get("type") for p in f.get("pads", [])}
    k = "smd" if "smd" in types else ("tht" if "th" in types else "none")
    print(f"{name.get(i, '')}\t{f.get('ref', '')}\t{k}")
