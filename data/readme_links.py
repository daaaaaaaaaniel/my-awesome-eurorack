#!/usr/bin/env python3
"""Shop / community / video links in README files (d, 2026-09-28 21:58).

  python3 data/readme_links.py > data/readme-links.tsv          (READMEs found from data/modules.tsv + data/trees)
     also rewrites ITS OWN cart lines in data/bom-links.tsv (see sync_carts; every other line there is left alone)
  python3 data/readme_links.py --list-readmes                     (just print the README list: repo, sha, readme, ids)
READMEs scanned for a row: every README* / index.md (md, markdown, txt, rst, adoc, org, or no extension) in the row's
scope (data/modulefiles.sh; not under node_modules / lib / .github / firmware / software), plus those in each folder
above the scope up to the repo root. `ids` = the rows whose scope holds the README or sits below it. index.html is left
out (some are interactive BOMs).

One output line per link: ids, repo, sha, readme, line, kind, domain, url, link_text, context, prev_line.
  kind     (carts are moved to data/bom-links.tsv, d 23:47) cart (saved parts list: Mouser project, Tayda saved cart, Digi-Key list; d 23:38 - other parts links are dropped),
           site / docs (only in d's hand additions, data/readme-links-add.tsv), shop (retailer / marketplace), parts (component suppliers: Mouser, SparkFun, PJRC, chip makers ...), community (ModularGrid, ModWiggler), video (YouTube, Vimeo),
           fab (a shared PCB project on a fab house), shop-? (host or link text says shop/store/buy/kit, or a product page - mostly makers' own shops; review)
  d 2026-09-28 22:20: links to Amazon, Intellijel, Raspberry Pi, Adafruit, obdev, TI, ST, Xiaomi, PJRC (not its forum),
  SparkFun and Hosa are dropped; 11 makers' own shops count as shop (D_SHOP); YouTube hosts read "YouTube".
  context  the paragraph (or list item / table row) holding the link, markdown kept, capped at 400 chars
  prev_line the nearest non-empty line above that paragraph when the paragraph is just the link (e.g. a "Buy:" heading)
A README at a repo root or a collection folder covers every row below it, so `ids` can list many rows."""
import concurrent.futures as cf, re, subprocess, sys, urllib.parse
KNOWN = [  # (host regex, kind)
    (r"elecrow\.com", "shop"), (r"tindie\.com", "shop"), (r"etsy\.com", "shop"), (r"thonk\.co\.uk", "shop"),
    (r"synthcube\.com", "shop"), (r"modularaddict\.com", "shop"), (r"exploding-shed\.com", "shop"), (r"3u-shop\.de", "shop"),
    (r"lectronz\.com", "shop"), (r"ebay\.[a-z.]+", "shop"), (r"perfectcircuit\.com", "shop"), (r"schneidersladen\.de", "shop"),
    (r"signalsounds\.com", "shop"), (r"analoguehaven\.com", "shop"), (r"detroitmodular\.com", "shop"), (r"control-voltage\.(com|net)|controlvoltage\.net", "shop"),
    (r"juno\.co\.uk", "shop"), (r"thomann\.[a-z.]+", "shop"), (r"reverb\.com", "shop"), (r"crowdsupply\.com", "shop"),
    (r"kickstarter\.com", "shop"), (r"bigcartel\.com", "shop"), (r"shopify\.com|myshopify\.com", "shop"), (r"gumroad\.com", "shop"),
    (r"ko-fi\.com/.+/shop", "shop"), (r"frequencycentral\.co\.uk", "shop"), (r"pusherman\.net", "shop"), (r"magpie-modular\.co\.uk", "shop"),
    (r"mouser\.[a-z.]+|digikey\.[a-z.]+|lcsc\.com|tme\.eu|farnell\.com|reichelt\.de|conrad\.[a-z.]+|aliexpress\.com|amazon\.[a-z.]+|sparkfun\.com|adafruit\.com|pjrc\.com|ti\.com|st\.com|gigadevice\.com|protosupplies\.com|raspberrypi\.com|princeton\.com\.tw|forge-tme\.com|obdev\.at|small-bear-electronics\.mybigcommerce\.com|smallbearelec\.com|taydaelectronics\.com|musikding\.de|banzaimusic\.com", "parts"),
    (r"modulargrid\.(net|org|com)", "community"), (r"modwiggler\.com|muffwiggler\.com|muffwoggler\.com", "community"),
    (r"youtube\.com|youtu\.be", "video"), (r"vimeo\.com", "video"),
    (r"oshpark\.com/shared_projects", "fab"), (r"pcbway\.com/project/shareproject", "fab"), (r"aisler\.net/.+/", "fab"),
]
KRE = [(re.compile(r"(^|\.)(" + h + r")$|(^|\.)(" + h + r")/", re.I), k) for h, k in KNOWN]
SHOPISH = re.compile(r"(^|[.-])(shop|store|boutique)[.-]|/(shop|store|products?|kits?)(/|$)", re.I)
BUYTEXT = re.compile(r"\b(buy|purchase|order (a|the|one)|get (a|the|one) kit|kits? (are |is )?(available|for sale)|for sale|in stock)\b", re.I)
URL = re.compile(r"""\[([^\]]*)\]\((https?://[^)\s]+)\)|<a\s[^>]*href=["'](https?://[^"']+)["'][^>]*>(.*?)</a>|(https?://[^\s<>"')\]]+)""", re.I | re.S)

def fetch(repo, sha, path):
    r = subprocess.run(["curl", "-sS", "-m", "60", "--fail", f"https://raw.githubusercontent.com/{repo}/{sha}/" + urllib.parse.quote(path)], capture_output=True)
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n") if r.returncode == 0 else None

def classify(url, text, para):
    host = urllib.parse.urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    hp = host + urllib.parse.urlparse(url).path
    if host.endswith(("github.com", "githubusercontent.com", "github.io")) or host in ("img.youtube.com", "i.ytimg.com", "cdn.shopify.com") or host.endswith(("amazonaws.com", "digitaloceanspaces.com", "autodesk.com")): return None, host   # images / file hosting, not shops
    if re.search(r"\.(jpe?g|png|gif|webp|svg)(\?|$)", url, re.I): return None, host      # an embedded image, not a link to a shop
    for rx, k in KRE:
        if rx.search(hp + "/"):
            # a shop link to generic components (jacks, pots, knobs, displays ...) is a parts source, not the module for sale
            if k == "shop" and re.search(r"/parts?/|thonkiconn|jacks?\b|jacks/|pots?\b|pots/|potentiometer|knobs?|headers?|display|oled|switch|cable|vactrol|spacer|standoff", (urllib.parse.urlparse(url).path + " " + (text or "")), re.I): return "parts", host
            return k, host
    if SHOPISH.search(host + urllib.parse.urlparse(url).path + "/") or BUYTEXT.search(text or ""): return "possible-shop", host
    return None, host

# d, 2026-09-28 22:20: rulings on the first run
D_DROP = re.compile(r"(^|\.)(amazon\.com|intellijel\.com|raspberrypi\.com|adafruit\.com|obdev\.at|ti\.com|st\.com|mi\.com|sparkfun\.com|hosatech\.com)$|^(www\.)?pjrc\.com$", re.I)
D_SHOP = re.compile(r"(^|\.)(electricdruid\.net|division-6\.com|bpcmusic\.com|ericasynths\.lv|bitiworkshop\.com|rebeltech\.org|winterbloom\.com|supersynthesis\.com|mysticcircuits\.com|system80\.net|allensynthesis\.square\.site)$", re.I)
# d, 2026-09-28 22:29: more makers' shops; Apple and Elektron out; bare shop front pages of Thonk / Tayda out (a link with
# specific content after the domain - /shop/..., /wp-content/..., /electromechanical... - stays)
D_SHOP2 = re.compile(r"(^|\.)(afterlateraudio\.com|calsynth\.com|northernlightmodular\.com|instruomodular\.com|extralifeinstruments\.com|aisynthesis\.com|oamodular\.org|gmsn\.co\.uk|tulip\.computer|pushermanproductions\.com)$", re.I)
D_DROP2 = re.compile(r"(^|\.)(apple\.com|elektron\.se|princeton\.com(\.[a-z]{2})?|protosupplies\.com)$", re.I)   # princeton: d 22:30; protosupplies: d 23:03
# d 23:03: repos whose README links are all replaced by d's own list in data/readme-links-add.tsv
D_DROP_REPO = {"TomWhitwell/Workshop_Computer"}
def bare_front(url):
    u = urllib.parse.urlparse(url); h = u.netloc.lower()
    if re.search(r"(^|\.)(thonk\.co\.uk|taydaelectronics\.com)$", h) and u.path.strip("/").lower() in ("", "quick-order"): return True
    # d 22:32: Digi-Key / Mouser home pages (nothing after the domain) out; product pages and Mouser projects stay
    return bool(re.search(r"(^|\.)(digikey|mouser)\.[a-z.]+$", h)) and not u.path.strip("/") and not u.query
CART = re.compile(r"mouser\.[a-z.]+/ProjectManager/|taydaelectronics\.com/savecartpro/|digikey\.[a-z.]+/(short/|mylists/|BOM)|lcsc\.com/bom|octopart\.com/bom-tool", re.I)
D_NAME = {"www.youtube.com": "YouTube", "youtu.be": "YouTube", "youtube.com": "YouTube", "m.youtube.com": "YouTube"}

def tindie_products(rows, here):
    """d 2026-09-28 23:06: a link to a Tindie STORE front page is split per row when data/tindie-products.tsv names that
    row's own product in the store (found by web search on Tindie titles): the row gets a line with the product URL, and
    the store line keeps only the rows with no product found. rows = list of output columns (header first)."""
    import csv, os
    tp = os.path.join(here, "tindie-products.tsv")
    if not os.path.exists(tp): return rows
    prod = {}
    for r in csv.DictReader(open(tp, newline="", encoding="utf-8"), delimiter="\t"):
        prod[(r["id"], r["store_url"].lower().rstrip("/"))] = r
    h = rows[0]; ii, iu, it, ic = h.index("ids"), h.index("url"), h.index("link_text"), h.index("context")
    out = [h]
    for r in rows[1:]:
        m = re.match(r"(https?://(www\.)?tindie\.com/stores/[^/?#]+)", r[iu], re.I)
        if not m: out.append(r); continue
        store = ("https://www.tindie.com/stores/" + m.group(1).rsplit("/", 1)[-1]).lower()
        ids = r[ii].split(","); hit = [i for i in ids if (i, store) in prod]; rest = [i for i in ids if i not in hit]
        if rest: out.append(r[:ii] + [",".join(rest)] + r[ii + 1:])
        for i in hit:
            p = prod[(i, store)]; n = list(r); n[ii] = i; n[iu] = p["product_url"]
            n[it] = p["tindie_title"]; n[ic] = f"[product found on Tindie for the store link {r[iu]} - {p['match']}] " + r[ic]
            out.append(n)
    return out

def url_fixes(rows, here):
    """d's corrections of wrong links in the source READMEs (data/readme-links-fix.tsv: id, readme, old_url, new_url,
    basis): that row's line from that README gets the new URL, and its context says so."""
    import csv, os
    fp = os.path.join(here, "readme-links-fix.tsv")
    if not os.path.exists(fp): return rows
    fx = {(r["id"], r["readme"], r["old_url"]): r for r in csv.DictReader(open(fp, newline="", encoding="utf-8"), delimiter="\t")}
    h = rows[0]; ii, ir, iu, ic = h.index("ids"), h.index("readme"), h.index("url"), h.index("context")
    for r in rows[1:]:
        for i in r[ii].split(","):
            f = fx.get((i, r[ir], r[iu]))
            if f and r[ii] == i:
                if f["new_url"] != f["old_url"]: r[iu] = f["new_url"]; r[ic] = f"[URL corrected by d: README links {f['old_url']}] " + r[ic]
                if (f.get("note") or "").strip(): r[ic] = f"[note (d): {f['note']}] " + r[ic]
    return rows

def narrow(rows, here):
    """d 2026-09-28 23:58: a link from a README shared by several rows (a collection's root README) that NAMES one of those
    rows - its link text, or the last part of its URL - belongs to that row only (Rebel Tech .../products/mix-01 -> Mix 01;
    Erica Synths "Dual VCA" -> Dual VCA). Exact name matches win; otherwise the longest module name contained in the URL's
    last part. A link that names none of its rows stays with all of them."""
    import csv, os
    names = {x["id"]: x["module_name"] for x in csv.DictReader(open(os.path.join(here, "modules.tsv"), newline="", encoding="utf-8"), delimiter="\t")}
    n = lambda t: re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", (t or "").lower()))   # "(THT)", "(10HP)", "(modified)" ... ignored
    h = rows[0]; ii, iu, it = h.index("ids"), h.index("url"), h.index("link_text"); out = [h]
    for r in rows[1:]:
        ids = r[ii].split(",")
        if len(ids) > 1:
            text = n(re.sub(r"<[^>]+>", "", r[it])); slug = n(urllib.parse.unquote(urllib.parse.urlparse(r[iu]).path.rstrip("/").rsplit("/", 1)[-1]))
            exact = [i for i in ids if n(names.get(i)) and n(names.get(i)) in (text, slug)]
            if not exact:
                cont = [(len(n(names.get(i))), i) for i in ids if len(n(names.get(i))) >= 4 and (n(names.get(i)) in slug or n(names.get(i)) in text)]
                if cont: best = max(c[0] for c in cont); exact = [i for L, i in cont if L == best]
            if exact: r = r[:ii] + [",".join(exact)] + r[ii + 1:]
        out.append(r)
    return out

def drop_links(rows, here):
    """d's removals of irrelevant links (data/readme-links-drop.tsv: id, url, basis): that url leaves that row; a line
    left with no rows is dropped."""
    import csv, os
    fp = os.path.join(here, "readme-links-drop.tsv")
    if not os.path.exists(fp): return rows
    D = list(csv.DictReader(open(fp, newline="", encoding="utf-8"), delimiter="\t"))   # id ("*" = every row), url, [readme], basis
    gone = lambda i, u, rd: any(d["url"] == u and d["id"] in (i, "*") and (not (d.get("readme") or "").strip() or d["readme"] == rd) for d in D)
    h = rows[0]; ii, iu, ir = h.index("ids"), h.index("url"), h.index("readme"); out = [h]
    for r in rows[1:]:
        ids = [i for i in r[ii].split(",") if not gone(i, r[iu], r[ir])]
        if ids: out.append(r[:ii] + [",".join(ids)] + r[ii + 1:])
    return out

def dedupe(rows):
    """d 2026-09-28 23:34: the same url for the same ids (e.g. p11 linking its shop from README.md and
    user_guide/docs/index.md) is kept once - the first line; which one does not matter (d)."""
    h = rows[0]; ii, iu = h.index("ids"), h.index("url"); seen = set(); out = [h]
    for r in rows[1:]:
        k = (r[ii], r[iu])
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

CART_TAG = "from README (readme_links.py): "
def cart_label(url):
    h = urllib.parse.urlparse(url).netloc.lower()
    return "Mouser cart" if "mouser" in h else "Tayda cart" if "tayda" in h else "Digi-Key list" if "digikey" in h else "LCSC BOM" if "lcsc" in h else "Octopart BOM" if "octopart" in h else "cart"

def sync_carts(rows, here):
    """d 2026-09-28 23:47: carts live in data/bom-links.tsv (the file the site reads for BOM links), not in
    readme-links.tsv. This keeps ITS OWN lines there (basis starts with CART_TAG): they are replaced on every run, every
    other line is left alone, and a (row, url) already in the file is not added again. Returns rows without the carts."""
    import os
    h = rows[0]; ii, iu, ik, ir, il = h.index("ids"), h.index("url"), h.index("kind"), h.index("readme"), h.index("line")
    carts = [r for r in rows[1:] if r[ik] == "cart"]; rest = [h] + [r for r in rows[1:] if r[ik] != "cart"]
    bp = os.path.join(here, "bom-links.tsv")
    lines = open(bp, encoding="utf-8").read().rstrip("\n").split("\n")
    keep = [l for l in lines if not (len(l.split("\t")) == 4 and l.split("\t")[3].startswith(CART_TAG))]
    have = {(l.split("\t")[0], l.split("\t")[1]) for l in keep if len(l.split("\t")) == 4}
    for r in carts:
        for i in r[ii].split(","):
            if (i, r[iu]) in have: continue
            have.add((i, r[iu]))
            keep.append("\t".join([i, r[iu], cart_label(r[iu]), (CART_TAG + f"{r[ir]}:{r[il]}").replace('"', "'").replace("\t", " ")]))
    open(bp, "w", encoding="utf-8").write("\n".join(keep) + "\n")
    return rest

def one(job):
    repo, sha, path, ids = job
    t = fetch(repo, sha, path)
    if t is None: return [f"#FETCHFAIL\t{repo}\t{sha}\t{path}"]
    t = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), t, flags=re.S)   # commented-out text is not shown on GitHub: ignore it (d 00:13)
    lines = t.split("\n"); out = []
    for n, ln in enumerate(lines):
        for m in URL.finditer(ln):
            url = m.group(2) or m.group(3) or m.group(5); text = m.group(1) or m.group(4) or ""
            url = url.rstrip(".,;:*_")
            kind, host = classify(url, text, ln)
            if not kind or D_DROP.search(host) or D_DROP2.search(host) or bare_front(url): continue
            if kind == "possible-shop": kind = "shop" if (D_SHOP.search(host) or D_SHOP2.search(host)) else "shop-?"
            # d 23:38: parts links go, except carts (a saved parts list you can order from): kind "cart"
            if CART.search(url): kind = "cart"
            elif kind == "parts": continue
            host = D_NAME.get(host, host)
            # d 22:44: one name per community site, whatever the host spelling
            if re.search(r"(^|\.)modulargrid\.(net|org|com)$", host, re.I): host = "modulargrid"
            elif re.search(r"(^|\.)(modwiggler|muffwiggler|muffwoggler)\.com$", host, re.I): host = "modwiggler"
            # d 22:47: one name per shop, whatever the host / country spelling
            elif re.search(r"(^|\.)mouser\.[a-z.]+$", host, re.I): host = "mouser"
            elif re.search(r"(^|\.)ebay\.[a-z.]+$", host, re.I): host = "ebay"
            elif re.search(r"(^|\.)aliexpress\.[a-z.]+$", host, re.I): host = "aliexpress"
            a = n                                   # paragraph: up to blank line; a list item / table row is its own paragraph
            if not re.match(r"\s*([-*+]|\d+\.|\|)\s", ln):
                while a > 0 and lines[a - 1].strip() and not re.match(r"\s*([-*+]|\d+\.|\||#)", lines[a - 1]): a -= 1
            b = n
            if not re.match(r"\s*([-*+]|\d+\.|\|)\s", ln):
                while b + 1 < len(lines) and lines[b + 1].strip() and not re.match(r"\s*([-*+]|\d+\.|\||#)", lines[b + 1]): b += 1
            para = " ".join(x.strip() for x in lines[a:b + 1]).strip()
            only = re.sub(r"\[[^\]]*\]\([^)]*\)|https?://\S+|<[^>]+>|[-*+|#>\s]", "", para) == re.sub(r"\W", "", text)
            prev = ""
            if a > 0 and (only or len(para) < 60):
                k = a - 1
                while k >= 0 and not lines[k].strip(): k -= 1
                prev = lines[k].strip() if k >= 0 else ""
            clean = lambda s: re.sub(r"\s+", " ", s.replace("\t", " "))[:400]
            out.append("\t".join([ids, repo, sha, path, str(n + 1), kind, host, url, clean(text), clean(para), clean(prev)]))
    return out

def readme_jobs():
    """(repo, sha, readme, ids) for every README a row of data/modules.tsv can see (folded in 2026-09-28 22:35, d)"""
    import collections, csv, os
    here = os.path.dirname(os.path.abspath(__file__)); csv.field_size_limit(10 ** 9)
    RD = re.compile(r"(^|/)(readme|index)[^/]*\.(md|markdown|txt|rst|adoc|org)$|(^|/)readme$", re.I)
    SKIP = re.compile(r"(^|/)(node_modules|lib|libs|\.github|firmware|software)/", re.I)
    found = collections.defaultdict(set); trees = {}
    for x in csv.DictReader(open(os.path.join(here, "modules.tsv"), newline="", encoding="utf-8"), delimiter="\t"):
        repo = x["repo"]
        if repo not in trees:
            tp = os.path.join(here, "trees", repo.replace("/", "_") + ".txt")
            trees[repo] = open(tp, encoding="utf-8").read().splitlines() if os.path.exists(tp) else []
        fs = subprocess.run(["bash", os.path.join(here, "modulefiles.sh"), repo, x["module_dir"] or "."], capture_output=True, text=True).stdout.splitlines()
        scope = fs[0].split("\t")[1] if fs and fs[0].startswith("SCOPE") else (x["module_dir"] or ".")
        own = [f for f in fs[1:] if RD.search(f) and not SKIP.search(f)]
        anc = []; d = scope if scope not in (".", "") else ""
        while True:                                   # the scope folder and every folder above it, up to the root
            anc += [f for f in trees[repo] if RD.search(f) and (f.rsplit("/", 1)[0] if "/" in f else "") == d]
            if not d: break
            d = d.rsplit("/", 1)[0] if "/" in d else ""
        for f in set(own + anc): found[(repo, x["sha"], f)].add(x["id"])
    return [[repo, sha, f, ",".join(sorted(ids, key=lambda i: int(i[1:])))] for (repo, sha, f), ids in sorted(found.items())]

if __name__ == "__main__":
    jobs = readme_jobs()
    if "--list-readmes" in sys.argv:
        for j in jobs: print("\t".join(j))
        sys.exit(0)
    import csv, os                 # fields holding '"' are quoted, inner quotes doubled (GitHub's TSV view needs it)
    here = os.path.dirname(os.path.abspath(__file__))
    rows = ["ids repo sha readme line kind domain url link_text context prev_line".split()]
    with cf.ThreadPoolExecutor(16) as ex:
        for res in ex.map(one, [j for j in jobs if j[0] not in D_DROP_REPO]):
            rows += [r.split("\t") for r in res]
    ap = os.path.join(here, "readme-links-add.tsv")   # d's hand additions (same columns), appended as they are
    if os.path.exists(ap): rows += list(csv.reader(open(ap, newline="", encoding="utf-8"), delimiter="\t"))[1:]
    rows = tindie_products(rows, here)
    rows = url_fixes(rows, here)
    rows = narrow(rows, here)
    rows = drop_links(rows, here)
    rows = dedupe(rows)
    rows = sync_carts(rows, here)   # side effect: data/bom-links.tsv gets the carts (its own tagged lines only)
    csv.writer(sys.stdout, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL).writerows(rows)
