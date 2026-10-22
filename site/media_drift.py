#!/usr/bin/env python3
"""Report mirrored media whose original repo has changed since the catalogue pin (d 2026-10-21).

    python3 site/media_drift.py          # after site/build.py; writes docs/media-drift.json

Run on every site build. It only REPORTS: the site keeps serving the pinned copies in data/media-lock.tsv,
and a change is taken in deliberately (re-check the catalogue row, move its pin, re-import, regenerate the
lock). One `git ls-remote` per repo (no download); only a repo whose default branch has moved gets one GitHub
API tree call (GH_TOKEN / GITHUB_TOKEN used when set), compared by Git blob ID. Network failures are reported
per repo, never fatal.
"""
import concurrent.futures, json, os, subprocess, sys, urllib.request
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, "data", "media-lock.tsv")
OUT = os.path.join(ROOT, "docs", "media-drift.json")

def branches():
    out = {}
    for l in open(os.path.join(ROOT, "data", "inventory.tsv"), encoding="utf-8"):
        f = l.rstrip("\r\n").split("\t")
        if len(f) >= 7 and f[1] != "repo":
            out[f[1]] = f[6] or "main"
    return out

def check(repo, pin, files, branch, token):
    r = {"repo": repo, "pin": pin, "branch": branch}
    try:
        p = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD", f"refs/heads/{branch}"],
                           capture_output=True, text=True, timeout=60, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        refs = {x.split("\t")[1]: x.split("\t")[0] for x in p.stdout.splitlines() if "\t" in x}
        head = refs.get(f"refs/heads/{branch}") or refs.get("HEAD")
        if p.returncode or not head:
            return {**r, "status": "unreachable", "error": (p.stderr.strip() or "no such branch")[-300:]}
        r["head"] = head
        if head == pin:
            return {**r, "status": "unchanged"}
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/git/trees/{head}?recursive=1",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "eurorack-media-drift",
                                              **({"Authorization": "Bearer " + token} if token else {})})
        with urllib.request.urlopen(req, timeout=30) as resp:
            tree = json.load(resp)
        now = {t["path"]: t["sha"] for t in tree.get("tree", []) if t.get("type") == "blob"}
        changed = sorted(p for p, b in files.items() if p in now and now[p] != b)
        gone = sorted(p for p in files if p not in now)
        if tree.get("truncated"):
            return {**r, "status": "moved, tree truncated (not compared)", "changed": changed}
        return {**r, "status": "media changed" if changed or gone else "moved, media unchanged", "changed": changed, "gone": gone}
    except Exception as e:
        return {**r, "status": "unreachable", "error": str(e)[-300:]}

def main():
    if not os.path.exists(LOCK):
        print("media drift: no data/media-lock.tsv, nothing to check"); return
    files, pins = defaultdict(dict), {}
    for l in open(LOCK, encoding="utf-8"):
        f = l.rstrip("\r\n").split("\t")
        if not l.startswith("#") and f[0] == "git":
            files[f[1]][f[2]] = f[4]; pins[f[1]] = f[3]
    br, token = branches(), os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(lambda repo: check(repo, pins[repo], files[repo], br.get(repo, "main"), token), sorted(files)))
    count = defaultdict(int)
    for x in res:
        count[x["status"]] += 1
    report = {"checked": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "repos": len(res), "counts": dict(count),
              "changes": [x for x in res if x["status"] != "unchanged"]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    lines = [f"media drift: {len(res)} repos checked - " + ", ".join(f"{n} {k}" for k, n in sorted(count.items()))]
    for x in report["changes"]:
        if x["status"] == "media changed":
            lines.append(f"  {x['repo']}: {len(x['changed'])} changed, {len(x['gone'])} gone since {x['pin'][:7]} - "
                         + ", ".join((x["changed"] + x["gone"])[:4]) + (" ..." if len(x["changed"]) + len(x["gone"]) > 4 else ""))
        elif x["status"] == "unreachable":
            lines.append(f"  {x['repo']}: unreachable ({x['error'][:80]})")
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("### Mirrored media drift\n\n```\n" + "\n".join(lines) + "\n```\n")

if __name__ == "__main__":
    main()
