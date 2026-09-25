#!/bin/bash
# For each line on stdin ("owner/repo" or "owner/repo<TAB>module_dir"): locate that
# module's README / LICENSE / BOM from the saved tree, fetch them raw, save signal lines.
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"
OUT="${OUT:-$DATA/readme-extracts}"
mkdir -p "$OUT"

while IFS=$'\t' read -r r dir; do
  [ -n "$r" ] || continue
  key=$(echo "$r" | tr '/' '_'); f="$TREES/$key.txt"
  [ -s "$f" ] || { echo "NO_TREE $r"; continue; }
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV"); br=${br:-main}

  # Scope to ONE module (see modulefiles.sh). Root module keeps the old filename, so
  # repo-level extracts are unchanged; a module in a subfolder gets <key>@<dir>.txt.
  mf=$(TREES="$TREES" bash "$DATA/modulefiles.sh" "$r" "$dir")
  scope=$(head -1 <<<"$mf" | cut -f2); files=$(tail -n +2 <<<"$mf")
  if [ "$scope" = "." ]; then out="$OUT/$key.txt"
  else out="$OUT/$key@$(echo "$scope" | tr '/ ' '__').txt"; fi
  { echo "### repo: $r   branch: $br   module: $scope"
    echo "### sha: $(awk -F'\t' -v R="$r" '$2==R{print $6}' "$INV")"
  } > "$out"

  shallowest() { grep -iE "$1" | awk -F/ '{print NF"\t"$0}' | sort -n | head -1 | cut -f2-; }
  # README / LICENSE: shallowest one inside the module; if the module has none, fall back
  # to the repo root (licences are usually declared once there), and say so.
  readme=$(shallowest '(^|/)readme(\.md|\.txt|\.rst)?$' <<<"$files"); rnote=""
  # GitHub Pages sites keep each module's text in index.md, not a README
  # (bummbummgarage.github.io: every design credit is in modules/<m>/index.md).
  [ -z "$readme" ] && readme=$(shallowest '(^|/)index\.md$' <<<"$files")
  [ -z "$readme" ] && { readme=$(grep -iE '^readme(\.md|\.txt|\.rst)?$' "$f" | head -1); [ -n "$readme" ] && rnote=" (repo root - none in module)"; }
  lic=$(shallowest '(^|/)(license|licence|copying)[^/]*$' <<<"$files"); lnote=""
  [ -z "$lic" ] && { lic=$(grep -iE '^(license|licence|copying)[^/]*$' "$f" | head -1); [ -n "$lic" ] && lnote=" (repo root - none in module)"; }
  boms=$(grep -iE '(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv|html)$' <<<"$files" | head -3)

  fetch() { curl -sS -m 25 --fail "https://raw.githubusercontent.com/$r/$br/$(echo "$1" | sed 's/ /%20/g')" 2>/dev/null; }

  if [ -n "$readme" ]; then
    echo "" >> "$out"; echo "=== README: $readme$rnote ===" >> "$out"
    fetch "$readme" | head -c 20000 | grep -inE \
      'through[- ]?hole|\bTHT\b|\bSMD\b|\bSMT\b|surface[- ]mount|0201|0402|0603|0805|1206|SOIC|SOT-23|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|DIP-?[0-9]|licen[cs]e|based on|inspired by|clone of|derived|adapted|remix|original design|version of|port of|stripboard|veroboard|protoboard|breadboard|gerber|BOM|bill of materials|\bHP\b|schematic|^#+ *(references|credits|thanks|acknowledg|sources?|prior art)|yusynth|kassu2000|kassutronics|pichenettes|mutable|electricdruid|electric druid|hagiwo|musicthing|music thing|lookmumnocomputer|thonk|barton|ken stone|cgs|mfos|schmitz|dintree|nonlinearcircuits|4ms|befaco' \
      | head -40 >> "$out"
    echo "--- brand/creator signals ---" >> "$out"
    fetch "$readme" | head -c 20000 | grep -inE \
      'tindie\.com|etsy\.com|designed by|design by|\(c\) 20|copyright|©|modular\.(com|net)|\.co\.uk|shop|store|instagram|patreon|my name is|i am |created by' \
      | head -12 >> "$out"
    echo "--- README head ---" >> "$out"
    fetch "$readme" | head -25 >> "$out"
  else
    echo "" >> "$out"; echo "=== README: NONE IN TREE ===" >> "$out"
  fi

  if [ -n "$lic" ]; then
    echo "" >> "$out"; echo "=== LICENSE: $lic$lnote ===" >> "$out"
    fetch "$lic" | head -5 >> "$out"
  else
    echo "" >> "$out"; echo "=== LICENSE: NONE IN TREE ===" >> "$out"
  fi

  if [ -n "$boms" ]; then
    echo "$boms" | while read -r b; do
      echo "" >> "$out"; echo "=== BOM: $b ===" >> "$out"
      fetch "$b" | head -30 >> "$out"
    done
  else
    echo "" >> "$out"; echo "=== BOM: NONE IN MODULE ===" >> "$out"
  fi
  echo "EXTRACTED $r :: $scope -> $(basename "$out")"
done
