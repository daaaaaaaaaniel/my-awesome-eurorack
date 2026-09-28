#!/usr/bin/env python3
"""CPL / SMT-assembly readiness of a .kicad_pcb (d, 2026-09-28 04:33 - trial).

Reads the board text on stdin (KiCad 5 "(module", KiCad 6+ "(footprint"). Per footprint it records
reference, side, attribute flags, pad kinds, schematic link and part-number fields, then grades
the board:

  parts-lcsc      CPL-ready and every SMD placement has an LCSC number (orderable at JLCPCB as-is)
  parts-mpn       CPL-ready and every SMD placement has some part number (MPN or distributor SKU:
                  turnkey assembly elsewhere; d 04:51 - Mouser itself does no assembly)
  cpl-ready       placements fine, part numbers missing on some SMD placements
  needs-cleanup   SMD pads without the smd attribute, SMD placements without a schematic link, or
                  REF** / blank / duplicate references among them
  no-smd          footprints but no SMD placements (THT-only board or panel)
  no-placements   no footprints that would be placed (panel art, outline only)

Panel boards are never checked (d, 2026-09-28 04:37: "panels are never going to be populated with
components"): pass the board's path as the first argument and a panel file name (panel, faceplate, frontplate - not bare "front",
which stacked designs use for a populated control board) prints grade=skipped-panel without reading the file.

Output: one line "key=value ..." summary, then (with -v) one line per problem footprint.
A "placement" = footprint not board_only / exclude_from_pos_files / virtual, with at least one pad.
Part number fields: LCSC, LCSC Part, JLCPCB, MPN, Manufacturer_Part_Number, MFR PN, PN, Part Number.
"""
import re, sys
from collections import Counter

PN_KEYS = re.compile(r'^(lcsc|lcsc[ _#-]?part(?:[ _#-]?(?:no|number|#))?|jlc(?:pcb)?(?:[ _-]?part)?|mpn|manufacturer[ _]?part[ _]?number|mfr[ _]?pn|mfr|pn|part[ _]?number|part[ _]?num|partnum|part[ _]?#|mouser|digikey|digi-key[ _]?pn)$', re.I)
# not parts: never placements whatever their attributes say
NOTPART = re.compile(r'MountingHole|Fiducial|TestPoint|Logo|Symbol|NetTie|SolderJumper|WEEE|ROHS|Hole|Graphic|Label|Pad_|Slot|Artwork|Image|Text', re.I)

def blocks(txt, head):
    """yield the text of every top-level (head ...) block, paren-matched, strings respected"""
    i = 0; n = len(txt); pat = "(" + head
    while True:
        i = txt.find(pat, i)
        if i < 0: return
        if txt[i + len(pat)] not in " \n\t\r":
            i += 1; continue
        d = 0; j = i; s = False
        while j < n:
            c = txt[j]
            if s:
                if c == "\\": j += 1
                elif c == '"': s = False
            elif c == '"': s = True
            elif c == "(": d += 1
            elif c == ")":
                d -= 1
                if d == 0: break
            j += 1
        yield txt[i:j + 1]; i = j + 1

def sval(x):
    x = x.strip()
    return x[1:-1] if x.startswith('"') and x.endswith('"') else x

def parse(fp):
    lib = sval(re.match(r'\((?:footprint|module)\s+("(?:[^"\\]|\\.)*"|\S+)', fp).group(1))
    layer = re.search(r'\(layer\s+"?([^")\s]+)', fp)
    ref = re.search(r'\(fp_text\s+reference\s+("(?:[^"\\]|\\.)*"|[^\s)]+)', fp) or \
          re.search(r'\(property\s+"Reference"\s+("(?:[^"\\]|\\.)*")', fp)
    attr = re.search(r'\(attr\s+([^)]*)\)', fp)
    at = set(attr.group(1).split()) if attr else set()
    pads = Counter(m.group(1) for m in re.finditer(r'\(pad\s+(?:"[^"]*"|\S+)\s+(smd|thru_hole|np_thru_hole|connect)', fp))
    props = {sval(k): sval(v) for k, v in re.findall(r'\(property\s+("(?:[^"\\]|\\.)*"|\S+)\s+("(?:[^"\\]|\\.)*")', fp)}
    return dict(lib=lib, layer=layer.group(1) if layer else "?", ref=sval(ref.group(1)) if ref else "",
                attr=at, pads=pads, linked=bool(re.search(r'\((?:path|sheetfile|sheetname)\s', fp)),
                pn=any(PN_KEYS.match(k) and v.strip() not in ("", "~", "-") for k, v in props.items()),
                lcsc=any((re.match(r"lcsc|jlc", k, re.I) or re.fullmatch(r"C\d{3,}", v.strip())) and re.fullmatch(r"C\d{3,}", v.strip())
                         for k, v in props.items() if PN_KEYS.match(k)))

def grade(txt):
    ver = re.search(r'\(version\s+(\d+)', txt)
    fps = [parse(b) for b in blocks(txt, "footprint")] or [parse(b) for b in blocks(txt, "module")]
    place, smdp, issues = [], [], []
    for f in fps:
        excluded = f["attr"] & {"board_only", "exclude_from_pos_files", "virtual"}
        if excluded or not f["pads"] or NOTPART.search(f["lib"]): continue
        place.append(f)
        has_smd_pad = f["pads"]["smd"] > 0
        has_th_pad = f["pads"]["thru_hole"] > 0
        if "smd" in f["attr"] or (has_smd_pad and not has_th_pad):
            smdp.append(f)
            if "smd" not in f["attr"]: issues.append(("smd pads, no smd attr", f))
    refs = Counter(f["ref"] for f in place)
    for f in smdp:
        if f["ref"] in ("", "REF**", "~") or refs[f["ref"]] > 1: issues.append(("bad/duplicate ref", f))
        if not f["linked"]: issues.append(("no schematic link", f))
    pn = sum(f["pn"] for f in smdp); lc = sum(f["lcsc"] for f in smdp)
    if not place: g = "no-placements"
    elif not smdp: g = "no-smd"
    elif issues: g = "needs-cleanup"
    elif lc == len(smdp): g = "parts-lcsc"
    elif pn == len(smdp): g = "parts-mpn"
    else: g = "cpl-ready"
    kinds = Counter(k for k, _ in issues)
    summ = (f"grade={g} kicad_version={ver.group(1) if ver else '?'} footprints={len(fps)} placements={len(place)} "
            f"smd_placements={len(smdp)} back_side={sum(f['layer'].startswith('B.') for f in smdp)} "
            f"smd_with_pn={pn} smd_with_lcsc={lc} linked={sum(f['linked'] for f in smdp)} "
            + " ".join(f"issue[{k.replace(' ', '_')}]={v}" for k, v in kinds.items()))
    return summ, issues

_PF = re.compile(r"panel|face_?plate|front_?plate|(^|[ _-])plate([ _.-]|$)", re.I)   # file name; not bare "front": stacked front boards carry parts
_PD = re.compile(r"(^|[ _-])(front[ _-]?)?panels?$", re.I)   # parent folder ending in "panel" (panel/, "Inkscape Panel/"),
                                                             # not "14HP_panel_and_expanders/" (O_C T4.1 expander boards)
class _Panel:
    def search(self, path):
        parts = path.split("/")
        return _PF.search(parts[-1]) or (len(parts) > 1 and _PD.search(parts[-2]))
PANEL_FILE = _Panel()

if __name__ == "__main__":
    path = next((a for a in sys.argv[1:] if not a.startswith("-")), "")
    if path and PANEL_FILE.search(path):
        print("grade=skipped-panel"); sys.exit(0)
    s, iss = grade(sys.stdin.read())
    print(s)
    if "-v" in sys.argv:
        for k, f in iss[:12]: print(f"  {k}: {f['ref'] or '(none)'} {f['lib']} attr={','.join(sorted(f['attr'])) or '-'} pads={dict(f['pads'])}")
