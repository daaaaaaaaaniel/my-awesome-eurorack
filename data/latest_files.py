#!/usr/bin/env python3
"""Keep only the latest version of each board among candidate files (one path per line on
stdin). Files are grouped by directory + a normalised stem: extension, a leading "fixed-",
version tokens (v1.2, rev3, R2, _1_) and dates (2022-12-26, 20180302) removed. Within a
group the kept file is: a "fixed-" copy over the original, then the highest version, then
the newest date, then the last path. Kept paths print as-is; superseded ones print as
"#SUP<TAB>path" so the caller can name them in the basis (user, 2026-09-26: revisions and
fixed- BOMs must never be counted together).
"""
import os, re, sys
VER = re.compile(r"(?:^|[ _.-])(?:v|ver|version|rev|r)[ _.-]?(\d+(?:\.\d+)*)[a-z]?(?=$|[ _.-])", re.I)
# Only "." joins version parts: "v2_170" is version 2 of board "170", not version 2.170
# (tiny_rack psu_v2_170 / psu_v2_250 are different expansion boards).
DATE = re.compile(r"(?:^|[ _.-])((?:19|20)\d\d)[-_.]?([01]\d)[-_.]?([0-3]\d)(?=$|[ _.-])")
def key(p):
    d, b = os.path.split(p); stem = os.path.splitext(b)[0].lower()
    fixed = bool(re.match(r"fixed[ _-]", stem)); stem = re.sub(r"^fixed[ _-]", "", stem)
    dm = DATE.search(stem); date = "".join(dm.groups()) if dm else ""
    stem = DATE.sub("", stem)
    vm = VER.search(stem); ver = tuple(int(x) for x in vm.group(1).split(".")) if vm else ()
    stem = VER.sub("", stem)
    stem = re.sub(r"[ _.-]+", "_", stem).strip("_")
    return (d.lower(), stem), (fixed, ver, date, p)
paths = [l.rstrip("\n") for l in sys.stdin if l.strip()]
groups = {}
for p in paths:
    g, rank = key(p); groups.setdefault(g, []).append((rank, p))
for g, items in groups.items():
    items.sort(); best = items[-1][1]
    for _, p in items:
        print(p if p == best else f"#SUP\t{p}")
