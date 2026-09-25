#!/bin/bash
# Determine components = THT | SMD | both from hard evidence.
#
# Pass A, in order of preference:
#   1. KiCad footprint library names in .kicad_pcb  (v6 "(footprint " and v5 "(module ")
#   2. the BOM's footprint/package column
# Panel hardware NEVER disqualifies an SMD marking (CLAUDE.md): pots, jacks, switches,
# LEDs, headers and mounting holes are excluded from the THT tally entirely.
# With SMD present: any THT IC -> both; else <=5 THT passives -> SMD, 6+ -> both.
#
# Input: "owner/repo" or "owner/repo<TAB>module_dir" per line on stdin.
#   Files are scoped to that ONE module by modulefiles.sh; without a dir the scope is the
#   repo's root module, never the whole repo, so a collection's boards are never pooled.
# Output TSV: repo, module_scope, verdict, basis, confidence, detector_version
DETECTOR_VERSION=10

DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"

# panel hardware / mechanical — never counted as THT passives
PANEL='Potentiometer|LED_THT|LED_D|Connector|PinHeader|Pin_Header|Jack|Switch|Button|MountingHole|TestPoint|Fiducial|Screw|Socket|Terminal|Encoder|Display|Buttons|NetTie|Logo|Symbol|WEEE|ROHS|SLOT'
SMD_PKG='_SMD|Package_SO|SOIC|SOT-23|SOT23|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|0201|0402|0603|0805|1206'
THT_PKG='_THT|DIP-|DIP_|TO-92|TO-220|DO-41|DO-35|Radial|Axial|7MM_RESISTOR|CAP-D'
# THT ICs / actives: any one of these beside SMD parts makes the build "both". Counted from
# ALL footprints, so a socketed DIP (dropped by PANEL's "Socket") still counts.
THT_IC='DIP-|DIP_|SIP-|SIP_|TO-92|TO-220'

while IFS=$'\t' read -r r dir; do
  [ -n "$r" ] || continue
  key=$(echo "$r" | tr '/' '_'); f="$TREES/$key.txt"
  [ -s "$f" ] || { printf '%s\t%s\t\tno tree\tDeferred\t%s\n' "$r" "${dir:-.}" "$DETECTOR_VERSION"; continue; }
  mf=$(TREES="$TREES" bash "$DATA/modulefiles.sh" "$r" "$dir")
  scope=$(head -1 <<<"$mf" | cut -f2)
  files=$(tail -n +2 <<<"$mf")
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV" | tr -d '\r'); br=${br:-main}
  fetch(){ curl -sS -m 40 "https://raw.githubusercontent.com/$r/$br/$(echo "$1" | sed 's/ /%20/g')" 2>/dev/null; }

  smd=0; tht=0; ic=0; src=""; thtic=0; tq=0

  # --- 1. KiCad footprints ---
  while read -r p; do
    [ -n "$p" ] || continue
    parts=$(fetch "$p" | python3 "$DATA/kicad_parts.py")   # footprint<TAB>reference
    fps=$(cut -f1 <<<"$parts")
    [ -n "$fps" ] || continue
    src="kicad footprints"
    keep=$(echo "$fps" | grep -vE "$PANEL")
    smd=$((smd + $(echo "$keep" | grep -cE "$SMD_PKG") ))
    tht=$((tht + $(echo "$keep" | grep -E "$THT_PKG" | grep -cvE "$THT_IC") ))
    # THT transistors (TO-92/TO-220 with a Q reference) count toward the passive limit,
    # like passives (user, 2026-09-26); other TO-/DIP/SIP parts are THT ICs.
    q=$(awk -F'\t' -v P="$THT_IC" '$1 ~ P && $1 ~ /TO-(92|220)/ && $2 ~ /^Q/' <<<"$parts" | grep -c .)
    tq=$((tq + q)); tht=$((tht + q))
    thtic=$((thtic + $(echo "$fps" | grep -cE "$THT_IC") - q))
    ic=$((ic  + $(echo "$fps"  | grep -cE 'Package_SO|SOIC|TSSOP|QFN|QFP') ))
  done < <(grep -iE '\.kicad_pcb$' <<<"$files" | head -4)

  # --- 2. BOM fallback ---
  if [ -z "$src" ]; then
    while read -r b; do
      [ -n "$b" ] || continue
      body=$(fetch "$b")
      [ -n "$body" ] || continue
      src="BOM $b"
      # count PARTS, not BOM lines: qty column, else designator count (bom_parts.py)
      rows=$(python3 "$DATA/bom_parts.py" <<<"$body")         # qty<TAB>refs<TAB>text
      sumq(){ awk -F'\t' -v P="$1" -v N="$2" -v Q="$3" 'BEGIN{IGNORECASE=1}
               $3 ~ P && (N=="" || $3 !~ N) && (Q=="" || $2 ~ Q) {s+=$1} END{print s+0}' <<<"$rows"; }
      smd=$((smd + $(sumq "$SMD_PKG" "$PANEL") ))
      tht=$((tht + $(awk -F'\t' -v P="$THT_PKG" -v N="$PANEL" -v I="$THT_IC" '$3 ~ P && $3 !~ N && $3 !~ I {s+=$1} END{print s+0}' <<<"$rows") ))
      q=$(sumq 'TO-(92|220)' '' '(^|[ ,;])Q[0-9]')          # Q designators = transistors
      tq=$((tq + q)); tht=$((tht + q))
      thtic=$((thtic + $(sumq "$THT_IC" '') - q))
      ic=$((ic  + $(sumq 'SOIC|TSSOP|QFN|QFP' '') ))
    done < <(grep -iE '(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv)$' <<<"$files" | head -2)
  fi

  if [ -z "$src" ]; then
    printf '%s\t%s\t\tno .kicad_pcb and no machine-readable BOM in scope\tDeferred\t%s\n' "$r" "$scope" "$DETECTOR_VERSION"; continue
  fi

  # --- verdict (user, 2026-09-26) ---
  # SMD present: any THT IC -> both; else <=5 THT passives -> SMD, 6+ -> both.
  # No SMD at all -> THT. Panel hardware never counts.
  conf=Strong
  if [ "$smd" -gt 0 ] && [ "$thtic" -gt 0 ]; then v=both
  elif [ "$smd" -gt 0 ] && [ "$tht" -le 5 ]; then v=SMD      # tht = passives + transistors
  elif [ "$smd" -gt 0 ]; then v=both
  elif [ "$tht" -gt 0 ] || [ "$thtic" -gt 0 ]; then v=THT
  else v=""; conf=Deferred; fi
  [ "$src" != "kicad footprints" ] && [ -n "$v" ] && conf=Stated

  printf '%s\t%s\t%s\t%s: smd=%s tht_passive=%s tht_transistor=%s tht_ic=%s (panel excluded) smd_ic=%s\t%s\t%s\n' \
    "$r" "$scope" "$v" "$src" "$smd" "$((tht - tq))" "$tq" "$thtic" "$ic" "$conf" "$DETECTOR_VERSION"
done
