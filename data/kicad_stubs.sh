#!/bin/bash
# A .kicad_pcb under 100 bytes is not a PCB (d, 2026-09-28): it is the empty board KiCad
# writes when a project is created ("(kicad_pcb (version 4) (host kicad \"dummy file\") )" is
# 51 bytes). Such files are treated as absent everywhere.
#
# This script measures every .kicad_pcb in the saved trees at the pinned commit (HTTP HEAD on
# raw.githubusercontent.com, so nothing is downloaded), records the stubs in
# data/kicad-stubs.tsv and removes them from data/trees/<key>.txt. Every reader of the trees
# (modulefiles.sh, moduledirs.sh, components.sh, panel_photos.py, generate.py, ...) therefore
# never sees them. clone_all.sh calls it for each newly saved tree.
#
#   usage: kicad_stubs.sh [owner/repo ...]     (no args: every tree)
#   A HEAD that is not HTTP 200 is reported on stderr and the file is left in the tree.
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TREES="${TREES:-$DATA/trees}"; INV="${INV:-$DATA/inventory.tsv}"; OUT="$DATA/kicad-stubs.tsv"
[ -s "$OUT" ] || printf 'repo\tsha\tpath\tbytes\n' > "$OUT"
if [ $# -eq 0 ]; then set -- $(tail -n +2 "$INV" | cut -f2 | tr -d '\r'); fi
for r in "$@"; do
  key=$(echo "$r" | tr '/' '_'); t="$TREES/$key.txt"; [ -s "$t" ] || continue
  ref=$(awk -F'\t' -v R="$r" '$2==R{print ($6!=""?$6:$7)}' "$INV" | tr -d '\r'); ref=${ref:-HEAD}
  grep -iE '\.kicad_pcb$' "$t" | while IFS= read -r p; do
    u="https://raw.githubusercontent.com/$r/$ref/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$p")"
    h=$(curl -sSI -m 30 "$u" 2>/dev/null | tr -d '\r')
    code=$(grep '^HTTP/' <<<"$h" | tail -1 | awk '{print $2}')   # last status line: a proxy adds its own 200 first
    n=$(awk -F': ' 'tolower($1)=="content-length"{print $2}' <<<"$h" | tail -1)
    if [ "$code" != "200" ]; then echo "kicad_stubs.sh: HTTP ${code:-none} for $r $p (left in tree)" >&2; continue; fi
    if [ -n "$n" ] && [ "$n" -lt 100 ]; then
      grep -qxF "$r"$'\t'"$ref"$'\t'"$p"$'\t'"$n" "$OUT" || printf '%s\t%s\t%s\t%s\n' "$r" "$ref" "$p" "$n" >> "$OUT"
    fi
  done
  # drop every recorded stub of this repo from its tree (idempotent)
  awk -F'\t' -v R="$r" 'NR>1 && $1==R {print $3}' "$OUT" > "$t.stubs"
  if [ -s "$t.stubs" ]; then grep -vxF -f "$t.stubs" "$t" > "$t.new"; mv "$t.new" "$t"; fi
  rm -f "$t.stubs"
done
