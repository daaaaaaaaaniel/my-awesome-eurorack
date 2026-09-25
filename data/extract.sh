#!/bin/bash
# For each repo given on stdin (owner/repo per line): locate README / LICENSE / BOM
# from the saved tree, fetch those files raw, and save signal lines.
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"
OUT="${OUT:-$DATA/readme-extracts}"
mkdir -p "$OUT"

while read -r r; do
  [ -n "$r" ] || continue
  key=$(echo "$r" | tr '/' '_'); f="$TREES/$key.txt"
  [ -s "$f" ] || { echo "NO_TREE $r"; continue; }
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV"); br=${br:-main}

  out="$OUT/$key.txt"
  { echo "### repo: $r   branch: $br"
    echo "### sha: $(awk -F'\t' -v R="$r" '$2==R{print $6}' "$INV")"
  } > "$out"

  # root README, root LICENSE, and up to 3 BOM files
  readme=$(grep -iE '^readme(\.md|\.txt|\.rst)?$' "$f" | head -1)
  [ -z "$readme" ] && readme=$(grep -iE '(^|/)readme[^/]*$' "$f" | head -1)
  lic=$(grep -iE '^(license|licence|copying)[^/]*$' "$f" | head -1)
  [ -z "$lic" ] && lic=$(grep -iE '(^|/)(license|licence|copying)[^/]*$' "$f" | head -1)
  boms=$(grep -iE '(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv|html)$' "$f" | head -3)

  fetch() { curl -sS -m 25 --fail "https://raw.githubusercontent.com/$r/$br/$(echo "$1" | sed 's/ /%20/g')" 2>/dev/null; }

  if [ -n "$readme" ]; then
    echo "" >> "$out"; echo "=== README: $readme ===" >> "$out"
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
    echo "" >> "$out"; echo "=== LICENSE: $lic ===" >> "$out"
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
    echo "" >> "$out"; echo "=== BOM: NONE IN TREE ===" >> "$out"
  fi
  echo "EXTRACTED $r"
done
