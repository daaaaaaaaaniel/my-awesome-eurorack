#!/bin/bash
# Determine components = THT | SMD | both from hard evidence.
#
# Pass A, in order of preference:
#   1. KiCad footprint library names in .kicad_pcb  (v6 "(footprint " and v5 "(module ")
#   2. the BOM's footprint/package column
# Panel hardware NEVER disqualifies an SMD marking (CLAUDE.md): pots, jacks, switches,
# LEDs, headers and mounting holes are excluded from the THT tally entirely.
# Threshold: with SMD present, <=3 THT parts still reads SMD; 4+ makes it both.
#
# Input: "owner/repo" or "owner/repo<TAB>module_dir" per line on stdin.
#   Files are scoped to that ONE module by modulefiles.sh; without a dir the scope is the
#   repo's root module, never the whole repo, so a collection's boards are never pooled.
# Output TSV: repo, module_scope, verdict, basis, confidence, detector_version
DETECTOR_VERSION=4

DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"

# panel hardware / mechanical — never counted as THT passives
PANEL='Potentiometer|LED_THT|LED_D|Connector|PinHeader|Pin_Header|Jack|Switch|Button|MountingHole|TestPoint|Fiducial|Screw|Socket|Terminal|Encoder|Display|Buttons|NetTie|Logo|Symbol|WEEE|ROHS|SLOT'
SMD_PKG='_SMD|Package_SO|SOIC|SOT-23|SOT23|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|0201|0402|0603|0805|1206'
THT_PKG='_THT|DIP-|DIP_|TO-92|TO-220|DO-41|DO-35|Radial|Axial|7MM_RESISTOR|CAP-D'

while IFS=$'\t' read -r r dir; do
  [ -n "$r" ] || continue
  key=$(echo "$r" | tr '/' '_'); f="$TREES/$key.txt"
  [ -s "$f" ] || { printf '%s\t%s\t\tno tree\tDeferred\t%s\n' "$r" "${dir:-.}" "$DETECTOR_VERSION"; continue; }
  mf=$(TREES="$TREES" bash "$DATA/modulefiles.sh" "$r" "$dir")
  scope=$(head -1 <<<"$mf" | cut -f2)
  files=$(tail -n +2 <<<"$mf")
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV" | tr -d '\r'); br=${br:-main}
  fetch(){ curl -sS -m 40 "https://raw.githubusercontent.com/$r/$br/$(echo "$1" | sed 's/ /%20/g')" 2>/dev/null; }

  smd=0; tht=0; ic=0; src=""

  # --- 1. KiCad footprints ---
  while read -r p; do
    [ -n "$p" ] || continue
    fps=$(fetch "$p" | grep -oE '\((footprint|module) "?[^" )]+' | sed -E 's/\((footprint|module) "?//')
    [ -n "$fps" ] || continue
    src="kicad footprints"
    keep=$(echo "$fps" | grep -vE "$PANEL")
    smd=$((smd + $(echo "$keep" | grep -cE "$SMD_PKG") ))
    tht=$((tht + $(echo "$keep" | grep -cE "$THT_PKG") ))
    ic=$((ic  + $(echo "$fps"  | grep -cE 'Package_SO|SOIC|TSSOP|QFN|QFP') ))
  done < <(grep -iE '\.kicad_pcb$' <<<"$files" | head -4)

  # --- 2. BOM fallback ---
  if [ -z "$src" ]; then
    while read -r b; do
      [ -n "$b" ] || continue
      body=$(fetch "$b")
      [ -n "$body" ] || continue
      src="BOM $b"
      keep=$(echo "$body" | grep -vE "$PANEL")
      smd=$((smd + $(echo "$keep" | grep -coE "$SMD_PKG") ))
      tht=$((tht + $(echo "$keep" | grep -coE "$THT_PKG") ))
      ic=$((ic  + $(echo "$body" | grep -coE 'SOIC|TSSOP|QFN|QFP') ))
    done < <(grep -iE '(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv)$' <<<"$files" | head -2)
  fi

  if [ -z "$src" ]; then
    printf '%s\t%s\t\tno .kicad_pcb and no machine-readable BOM in scope\tDeferred\t%s\n' "$r" "$scope" "$DETECTOR_VERSION"; continue
  fi

  # --- verdict, with the 3-part threshold ---
  conf=Strong
  if [ "$smd" -gt 0 ] && [ "$tht" -le 3 ]; then v=SMD
  elif [ "$smd" -gt 0 ] && [ "$tht" -gt 3 ]; then v=both
  elif [ "$tht" -gt 0 ]; then v=THT
  else v=""; conf=Deferred; fi
  [ "$src" != "kicad footprints" ] && [ -n "$v" ] && conf=Stated

  printf '%s\t%s\t%s\t%s: smd=%s tht=%s (panel excluded) smd_ic=%s\t%s\t%s\n' \
    "$r" "$scope" "$v" "$src" "$smd" "$tht" "$ic" "$conf" "$DETECTOR_VERSION"
done
