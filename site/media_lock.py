#!/usr/bin/env python3
"""Write data/media-lock.tsv from a media import's ASSET-MANIFEST.json (branch website-media-mirror, d 2026-10-21).

    python3 site/media_lock.py <media checkout> [--repo daaaaaaaaaniel/eurorack-meta-test] [--branch NAME]

The media commit is read from the checkout's HEAD, so the lock always names a commit that exists, and every
row is copied from the manifest - nothing is typed. build.py reads the lock (see "Mirrored media" there).
"""
import argparse, json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "media-lock.tsv")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout")
    ap.add_argument("--repo", default="daaaaaaaaaniel/eurorack-meta-test")
    ap.add_argument("--branch", help="branch name on GitHub, when the local one differs")
    a = ap.parse_args()
    git = lambda *x: subprocess.check_output(["git", "-C", a.checkout, *x], text=True).strip()
    commit, branch = git("rev-parse", "HEAD"), a.branch or git("rev-parse", "--abbrev-ref", "HEAD")
    assert not git("status", "--porcelain", "--untracked-files=no"), "media checkout has uncommitted changes to tracked files"
    manifest = json.load(open(os.path.join(a.checkout, "ASSET-MANIFEST.json"), encoding="utf-8"))
    rows = []
    for m in manifest:
        for v in (m.get("source_repo", ""), m.get("source_path", ""), m.get("source_url", ""), m["destination"]):
            assert "\t" not in v and "\n" not in v, v
        if "source_repo" in m:
            rows.append(("git", m["source_repo"], m["source_path"], m["source_pin"], m["source_git_blob"], str(m["bytes"]), m["sha256"], m["destination"]))
        else:
            rows.append(("url", m["source_url"], "", "", "", str(m["bytes"]), m["sha256"], m["destination"]))
    rows.sort()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"# media_repo\t{a.repo}\n# media_commit\t{commit}\n# media_branch\t{branch}\n")
        f.write("# kind\tsource\tpath\tsource_pin\tgit_blob\tbytes\tsha256\tdestination\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"wrote {len(rows)} rows to {os.path.relpath(OUT, ROOT)} ({a.repo} @ {commit[:7]}, {branch})")

if __name__ == "__main__":
    main()
