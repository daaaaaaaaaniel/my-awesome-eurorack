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
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV" | tr -d '\r'); br=${br:-main}
  # fetch at the pinned commit, so the extract describes the SHA the row will record
  sha=$(awk -F'\t' -v R="$r" '$2==R{print $6}' "$INV" | tr -d '\r'); ref=${sha:-$br}

  # Scope to ONE module (see modulefiles.sh). Root module keeps the old filename, so
  # repo-level extracts are unchanged; a module in a subfolder gets <key>@<dir>.txt.
  mf=$(TREES="$TREES" bash "$DATA/modulefiles.sh" "$r" "$dir")
  scope=$(head -1 <<<"$mf" | cut -f2); files=$(tail -n +2 <<<"$mf")
  if [ "$scope" = "." ]; then out="$OUT/$key.txt"
  else out="$OUT/$key@$(echo "$scope" | tr '/ ' '__').txt"; fi
  { echo "### repo: $r   branch: $br   module: $scope"
    echo "### sha: $sha (files fetched at this commit)"
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

  fetch() { curl -sS -m 25 --fail "https://raw.githubusercontent.com/$r/$ref/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$1")" 2>/dev/null; }

  if [ -n "$readme" ]; then
    echo "" >> "$out"; echo "=== README: $readme$rnote ===" >> "$out"
    rd=$(fetch "$readme") || echo "(README fetch FAILED at $ref - re-run; not evidence of absence)" >> "$out"
    head -c 20000 <<<"$rd" | grep -inE \
      'through[- ]?hole|\bTHT\b|\bSMD\b|\bSMT\b|surface[- ]mount|0201|0402|0603|0805|1206|SOIC|SOT-23|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|DIP-?[0-9]|licen[cs]e|based on|inspired by|clone of|derived|adapted|remix|original design|version of|port of|stripboard|veroboard|protoboard|breadboard|gerber|BOM|bill of materials|\bHP\b|schematic|^#+ *(references|credits|thanks|acknowledg|sources?|prior art)|yusynth|kassu2000|kassutronics|pichenettes|mutable|electricdruid|electric druid|hagiwo|musicthing|music thing|lookmumnocomputer|thonk|barton|ken stone|cgs|mfos|schmitz|dintree|nonlinearcircuits|4ms|befaco' \
      | head -40 >> "$out"
    echo "--- brand/creator signals ---" >> "$out"
    head -c 20000 <<<"$rd" | grep -inE \
      'tindie\.com|etsy\.com|designed by|design by|\(c\) 20|copyright|©|modular\.(com|net)|\.co\.uk|shop|store|instagram|patreon|my name is|i am |created by' \
      | head -12 >> "$out"
    echo "--- README head ---" >> "$out"
    head -25 <<<"$rd" >> "$out"
  else
    echo "" >> "$out"; echo "=== README: NONE IN TREE ===" >> "$out"
  fi

  # Page front matter (user-facing module text outside any README): Hugo/R-markdown sites
  # keep title / subtitle / author / references / draft in index.rmd or index.md YAML
  # (spielhuus/elektrophon: src/<m>/index.rmd). Print only those keys.
  page=$(shallowest '(^|/)index\.(rmd|md)$' <<<"$files")
  if [ -n "$page" ]; then
    echo "" >> "$out"; echo "=== FRONT MATTER: $page ===" >> "$out"
    fetch "$page" | python3 -c '
import sys,re
t=sys.stdin.read()
if not t.startswith("---"): print("(no YAML front matter)"); sys.exit()
fm=t.split("---")[1]
for k in ("title","subtitle","author","date","draft","excerpt","description"):
    m=re.search(r"^"+k+r":\s*(.*)$",fm,re.M)
    if m: print(k+": "+m.group(1).strip()[:300])
for d,ti in re.findall(r"description:\s*\"([^\"]*)\",\s*\n?\s*title:\s*\"([^\"]*)\"",fm):
    print("reference: "+ti[:80]+" / "+d[:80])
' >> "$out"
  fi

  if [ -n "$lic" ]; then
    echo "" >> "$out"; echo "=== LICENSE: $lic$lnote ===" >> "$out"
    lt=$(fetch "$lic") || echo "(LICENSE fetch FAILED at $ref)" >> "$out"
    head -5 <<<"$lt" >> "$out"
  else
    echo "" >> "$out"; echo "=== LICENSE: NONE IN TREE ===" >> "$out"
  fi

  if [ -n "$boms" ]; then
    echo "$boms" | while read -r b; do
      echo "" >> "$out"; echo "=== BOM: $b ===" >> "$out"
      bt=$(fetch "$b") || echo "(BOM fetch FAILED at $ref)" >> "$out"
      head -30 <<<"$bt" >> "$out"
    done
  else
    echo "" >> "$out"; echo "=== BOM: NONE IN MODULE ===" >> "$out"
  fi
  echo "EXTRACTED $r :: $scope -> $(basename "$out")"
done
