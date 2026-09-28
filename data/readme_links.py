#!/usr/bin/env python3
"""Shop / community / video links in README files (d, 2026-09-28 21:58).

  python3 data/readme_links.py < jobs.tsv > data/readme-links.tsv
  jobs.tsv: repo<TAB>sha<TAB>readme_path<TAB>ids   (ids = the rows whose scope holds the README or sits below it)

One output line per link: ids, repo, sha, readme, line, kind, domain, url, link_text, context, prev_line.
  kind     shop (retailer / marketplace), parts (component suppliers: Mouser, SparkFun, PJRC, chip makers ...), community (ModularGrid, ModWiggler), video (YouTube, Vimeo),
           fab (a shared PCB project on a fab house), possible-shop (host or link text says shop/store/buy/kit, or a product page - mostly makers' own shops; review)
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

def one(job):
    repo, sha, path, ids = job
    t = fetch(repo, sha, path)
    if t is None: return [f"#FETCHFAIL\t{repo}\t{sha}\t{path}"]
    lines = t.split("\n"); out = []
    for n, ln in enumerate(lines):
        for m in URL.finditer(ln):
            url = m.group(2) or m.group(3) or m.group(5); text = m.group(1) or m.group(4) or ""
            url = url.rstrip(".,;:*_")
            kind, host = classify(url, text, ln)
            if not kind: continue
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

if __name__ == "__main__":
    jobs = [l.rstrip("\n").split("\t") for l in sys.stdin if l.strip()]
    import csv                     # fields holding '"' are quoted, inner quotes doubled (GitHub's TSV view needs it)
    w = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow("ids repo sha readme line kind domain url link_text context prev_line".split())
    with cf.ThreadPoolExecutor(16) as ex:
        for res in ex.map(one, jobs):
            for r in res: w.writerow(r.split("\t"))
