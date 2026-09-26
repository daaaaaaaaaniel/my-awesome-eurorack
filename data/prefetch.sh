#!/bin/bash
# Fetch ALL evidence for the bulk run up front, so the enrichment session never waits on
# the network: components.sh -> data/components-out.tsv, extract.sh -> data/readme-extracts/.
#
# Resumable and idempotent: (repo, module_dir) pairs already in components-out.tsv and
# extracts that already exist are skipped, so re-running after a failure only does the
# rest. Rows whose basis says "fetch failed" are re-done on the next run (RETRY=1 default).
#
#   bash data/prefetch.sh            # every "todo" line of data/runlist.tsv
#   bash data/prefetch.sh 1 2        # only tiers 1 and 2
#   JOBS=4 bash data/prefetch.sh     # parallel workers (default 4)
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RL="${RL:-$DATA/runlist.tsv}"; CO="${CO:-$DATA/components-out.tsv}"; EX="${EX:-$DATA/readme-extracts}"   # env overrides for tests
JOBS="${JOBS:-4}"; RETRY="${RETRY:-1}"
[ -s "$RL" ] || { echo "no runlist - run python3 data/runlist.py first" >&2; exit 1; }
[ -s "$CO" ] || printf 'repo\tmodule_scope\tcomponents\tcomp_basis\tcomp_conf\tdetector_version\n' > "$CO"
tiers="${*:-1 2 3 4}"

# work = todo lines of the chosen tiers, minus pairs already fetched (unless they failed)
work=$(mktemp)
python3 - "$RL" "$CO" "$EX" "$RETRY" $tiers > "$work" <<'EOF'
import csv, os, sys
rl, co, ex, retry, *tiers = sys.argv[1:]
have = {}
for r in csv.DictReader(open(co), delimiter="\t"):
    # the scope column may carry a "[filter]" suffix; key on the bare dir
    have[(r["repo"], r["module_scope"].split(" [")[0])] = r["comp_basis"]
for r in csv.DictReader(open(rl), delimiter="\t"):
    if r["status"] != "todo" or r["tier"] not in tiers:
        continue
    k = (r["repo"], r["module_dir"])
    b = have.get(k)
    if b is not None and not (retry == "1" and "fetch failed" in b):
        continue
    print(r["repo"], "" if r["module_dir"] == "." else r["module_dir"], sep="\t")
EOF
n=$(grep -c . "$work"); echo "prefetch: $n module dirs to fetch (tiers: $tiers, jobs: $JOBS)" >&2
[ "$n" -gt 0 ] || { rm -f "$work"; exit 0; }

# 1. components: parallel workers (see below for durability)
parts=$(mktemp -d)
split -n l/"$JOBS" "$work" "$parts/w."
# each worker appends its own results as soon as ITS part finishes (one O_APPEND write), so a
# killed call loses at most the unfinished parts; readers take the LAST line per (repo, scope)
for w in "$parts"/w.*; do ( bash "$DATA/components.sh" < "$w" > "$w.out" 2> "$w.err"; cat "$w.out" >> "$CO" ) & done; wait
# a re-fetched pair (retry of "fetch failed") supersedes its older line
python3 - "$CO" <<'EOF'
import sys
co = sys.argv[1]; lines = [l.rstrip("\n") for l in open(co) if l.strip()]
hdr, last = lines[0], {}
for l in lines[1:]:
    f = l.split("\t"); last[(f[0], f[1].split(" [")[0])] = l   # last line per key wins
open(co, "w").write("\n".join([hdr] + list(last.values())) + "\n")
print(f"components-out.tsv: {len(last)} rows (deduped, last wins)")
EOF
cat "$parts"/w.*.err >&2

# 2. extracts: skip modules whose extract file exists and has no FAILED marker
ex_work=$(mktemp)
while IFS=$'\t' read -r r d; do
  key=$(echo "$r" | tr '/' '_')
  if [ -z "$d" ]; then f="$EX/$key.txt"; else f="$EX/$key@$(echo "$d" | tr '/ ' '__').txt"; fi
  # modulefiles.sh may resolve "." to the single subfolder; extract.sh names the file by the
  # resolved scope, so a root request can legitimately produce a "@dir" file - accept either
  if [ -s "$f" ] && ! grep -q 'fetch FAILED' "$f"; then continue; fi
  if [ -z "$d" ] && ls "$EX/$key@"*.txt >/dev/null 2>&1 && ! grep -lq 'fetch FAILED' "$EX/$key@"*.txt 2>/dev/null; then continue; fi
  printf '%s\t%s\n' "$r" "$d"
done < "$work" > "$ex_work"
echo "prefetch: $(grep -c . "$ex_work") extracts to fetch" >&2
split -n l/"$JOBS" "$ex_work" "$parts/e."
for w in "$parts"/e.*; do OUT="$EX" bash "$DATA/extract.sh" < "$w" > "$w.out" 2> "$w.err" & done; wait
cat "$parts"/e.*.err >&2
echo "prefetch: done. failed fetches still pending: $(grep -c 'fetch failed' "$CO") components, $(grep -l 'fetch FAILED' "$EX"/*.txt 2>/dev/null | wc -l) extracts" >&2
rm -rf "$work" "$ex_work" "$parts"
