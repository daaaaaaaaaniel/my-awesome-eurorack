#!/usr/bin/env python3
"""Deferred-pass helper: evidence for 'what does this module do?' in <= ~20 lines.

  python3 data/peek.py 'owner/repo' 'module/dir' [more pairs...]

Prints the module's own README/.md lines, function keywords found in its schematic PDFs
(pdftotext), and the IC part numbers in its Eagle/KiCad schematics or boards.
Fetches at the pinned SHA; read-only.
"""
import os, re, subprocess, sys, tempfile, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
inv = {}
for l in open(os.path.join(HERE, "inventory.tsv"), encoding="utf-8"):
    f = l.rstrip("\r\n").split("\t")
    if len(f) >= 7: inv[f[1]] = f[5]
KW = re.compile(r"\b(vcf|vco|lfo|vca|dco|envelope|adsr|mixer|filter|delay|reverb|echo|oscillat\w*|sequencer|noise|clock|"
                r"divider|multiplier|gate|trigger|random|quantiz\w*|expander|midi|attenu\w*|offset|logic|switch|wave\s?fold\w*|"
                r"ring\s?mod\w*|phaser|chorus|flanger|compressor|distortion|fuzz|overdrive|drum|kick|snare|hi.?hat|cymbal|clap|"
                r"preamp|follower|slew|portamento|sample|hold|s&h|t&h|buffer|mult\w*|comparator|rectifier|vactrol|lpg|"
                r"low.?pass|high.?pass|band.?pass|formant|vocoder|granular|looper|looping|bernoulli|probability|euclid\w*|"
                r"arpeggiat\w*|scope|tuner|power supply|psu|bus ?board|headphone|output|input|interface|joystick|touch)\b", re.I)
IC = re.compile(r"\b(LM13700|LM3900|LM358|LM324|TL07[1-4]|TL08[1-4]|NE5532|OPA\d+|MCP\d+|CD4\d{3}|74HC\w+|PT2399|FV-?1|"
                r"SSM21\d\d|V2164|AS33\d\d|CEM33\d\d|SSI21\d\d|AS2164|LM386|NE555|LM555|TL431|LM317|LM337|78\d\d|79\d\d|"
                r"ATMEGA\w+|ATTINY\w+|STM32\w+|RP20\d\d|ESP32\w*|TEENSY\w*|ARDUINO\w*|DAISY|AD\d{3,4}|DAC\d+|LM2907|"
                r"CA3080|CA3280|LM394|THAT\d+|BBD|MN3\d+|BL3\d+|VTL5C\d|NSL-?32)\b", re.I)

def fetch(repo, path, out):
    url = f"https://raw.githubusercontent.com/{repo}/{inv.get(repo,'HEAD')}/{urllib.parse.quote(path)}"
    return subprocess.run(["curl", "-s", "-m", "40", "--fail", "-o", out, url]).returncode == 0

def peek(repo, d):
    tree = open(os.path.join(HERE, "trees", repo.replace("/", "_") + ".txt"), encoding="utf-8").read().splitlines()
    files = [p for p in tree if d in (".", "") or p.startswith(d + "/")]
    print(f"### {repo} | {d} | {len(files)} files")
    tmp = tempfile.mkdtemp()
    mds = [p for p in files if re.search(r"(readme|index|about|info)[^/]*\.(md|txt|rmd|html?)$", p, re.I) and p.count("/") <= d.count("/") + 2][:2]
    for p in mds:
        t = os.path.join(tmp, "r")
        if fetch(repo, p, t):
            L = [re.sub(r"<[^>]+>", " ", l).strip() for l in open(t, encoding="utf-8", errors="replace")]
            L = [l for l in L if len(l) > 3 and not l.startswith(("![", "[!", "|--", "```"))]
            for l in L[:6]: print("  md:", l[:150])
            hits = [l for l in L[6:60] if KW.search(l)][:3]
            for l in hits: print("  md+:", l[:150])
    pdfs = [p for p in files if p.lower().endswith(".pdf")][:3]
    for p in pdfs:
        t = os.path.join(tmp, "s.pdf")
        if fetch(repo, p, t):
            txt = subprocess.run(["pdftotext", "-l", "3", t, "-"], capture_output=True, text=True).stdout
            kws = sorted({m.group(0).lower() for m in KW.finditer(txt)})
            ics = sorted({m.group(0).upper() for m in IC.finditer(txt)})
            title = [l.strip() for l in txt.splitlines() if re.match(r"\s*(title|sheet)\s*[:\-]", l, re.I)][:2]
            print(f"  pdf {os.path.basename(p)[:50]}: kw={','.join(kws[:12])} ic={','.join(ics[:10])} {' / '.join(title)[:80]}")
    srcs = [p for p in files if re.search(r"\.(sch|kicad_sch|brd|kicad_pcb)$", p, re.I)][:3]
    ics = set(); kws = set()
    for p in srcs:
        t = os.path.join(tmp, "e")
        if fetch(repo, p, t):
            txt = open(t, encoding="utf-8", errors="replace").read()
            ics |= {m.group(0).upper() for m in IC.finditer(txt)}
            for m in re.finditer(r'(?:<description>|"Title"|\(title |title_block|TITLE)\s*"?([^"<\n]{3,60})', txt): kws.add(m.group(1).strip())
    if srcs: print(f"  eda: ic={','.join(sorted(ics)[:14])} titles={'; '.join(sorted(kws)[:3])[:120]}")
    names = sorted({os.path.basename(p) for p in files if re.search(r"\.(pdf|kicad_pcb|brd|sch|kicad_sch|csv|xlsx?)$", p, re.I)})[:8]
    print("  names:", ", ".join(names)[:220])

args = sys.argv[1:]
for i in range(0, len(args), 2): peek(args[i], args[i + 1])
