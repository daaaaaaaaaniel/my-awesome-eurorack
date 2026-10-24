#!/usr/bin/env python3
"""Fetch a module's web page (or a file it links) and record what was read - the off-GitHub evidence for
web-sourced rows (retirement step 3, d 2026-10-23: 'if they have linked websites outside of github, its ok
to use that').

  python3 data/web_fetch.py PAGE_URL                  fetch a page; record it and every link / image on it
  python3 data/web_fetch.py --from PAGE_URL FILE_URL  fetch a file the page links (schematic, photo, ...);
                                                      refused unless FILE_URL was found on that page

Writes data/web-sources.tsv (url, final_url, status, content_type, bytes, sha256, fetched, found_on) and, for
HTML pages, data/web-links.tsv (page, link) - every a href / img src, resolved against the page. A re-fetch
replaces the url's lines. The bytes go to data/web-cache/<sha256> (git-ignored: these pages are other people's
copyright work; the hash proves which bytes the row's evidence was read from).

A web row in modules.tsv copies from here, never types: repo = the host, module_dir = the path, sha =
'sha256:' + the first 12 hex, date = the fetch date. generate.py checks all three, and that every URL in
schematic / photos / build is a fetched link of the row's page.
"""
import csv, datetime, hashlib, html, os, re, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, LINKS, CACHE = (os.path.join(HERE, n) for n in ("web-sources.tsv", "web-links.tsv", "web-cache"))
SRC_COLS = ["url", "final_url", "status", "content_type", "bytes", "sha256", "fetched", "found_on"]


def read(path, cols):
    if not os.path.exists(path): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def links_of(body, base, ctype):
    m = re.search(r"charset=([\w-]+)", ctype or "")
    t = body.decode(m.group(1) if m else "utf-8", errors="replace")
    t = re.sub(r"(?is)<script.*?</script>|<!--.*?-->", "", t)
    out = []
    for u in re.findall(r"""(?i)<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*["']?([^"'\s>]+)""", t):
        u = urllib.parse.urljoin(base, html.unescape(u)).split("#")[0]
        if u.startswith(("http://", "https://")) and u not in out: out.append(u)
    return out


def fetch(url, found_on=""):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (eurorack-open-source table; evidence fetch)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body, status, final, ctype = r.read(), r.status, r.geturl(), r.headers.get("Content-Type", "")
    sha = hashlib.sha256(body).hexdigest()
    os.makedirs(CACHE, exist_ok=True)
    open(os.path.join(CACHE, sha), "wb").write(body)
    rec = {"url": url, "final_url": final, "status": str(status), "content_type": ctype, "bytes": str(len(body)),
           "sha256": sha, "fetched": datetime.date.today().isoformat(), "found_on": found_on}
    src = [r for r in read(SRC, SRC_COLS) if r["url"] != url] + [rec]
    write(SRC, SRC_COLS, sorted(src, key=lambda r: (r["found_on"] or r["url"], r["found_on"] != "", r["url"])))
    if "html" in ctype.lower():
        lk = [r for r in read(LINKS, ["page", "link"]) if r["page"] != url]
        lk += [{"page": url, "link": u} for u in links_of(body, final, ctype)]
        write(LINKS, ["page", "link"], lk)
    print(f"{status} {len(body)} sha256:{sha[:12]} {url}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--from"]:
        page, files = a[1], a[2:]
        known = {r["link"] for r in read(LINKS, ["page", "link"]) if r["page"] == page}
        if not known: sys.exit(f"web_fetch.py: fetch the page first: {page}")
        for u in files:
            if u not in known: sys.exit(f"web_fetch.py: not a link on {page}: {u}")
            fetch(u, page)
    else:
        for u in a: fetch(u)
