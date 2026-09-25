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
DETECTOR_VERSION=13

DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"

# panel hardware / mechanical — never counted as THT passives
PANEL='Potentiometer|LED_THT|LED_D|Connector|PinHeader|Pin_Header|Jack|Switch|Button|MountingHole|TestPoint|Fiducial|Screw|Socket|Terminal|Encoder|Display|Buttons|NetTie|Logo|Symbol|WEEE|ROHS|SLOT'
SMD_PKG='_SMD|Package_SO|SOIC|SOT-23|SOT23|SOT-?223|SOT-?89|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|0201|0402|0603|0805|1206'
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

  # A KiCad file with no counted parts (e.g. a panel-only .kicad_pcb) does not hide an
  # EasyEDA circuit: fall through (Testbild-synth/headphone).
  [ "$src" = "kicad footprints" ] && [ $((smd + tht + thtic)) -eq 0 ] && src=""
  # --- 1b. EasyEDA JSON (no KiCad) ---
  # PCB JSON preferred (docType 3); schematic JSON only when no PCB JSON exists, so parts are
  # never counted twice. easyeda_parts.py collapses multi-unit parts by designator.
  # A package that is none of panel / SMD / THT leaves the call unmade (Weak -> blank).
  unk=""
  if [ -z "$src" ]; then
    ej=$(grep -iE '\.json$' <<<"$files" | grep -viE 'package\.json|\.vscode|tsconfig|manifest' | head -8)
    epcb=""; esch=""
    while read -r j; do
      [ -n "$j" ] || continue
      head=$(fetch "$j" | head -c 400)
      grep -q 'editorVersion' <<<"$head" || continue
      if grep -qE '"docType": ?"?3' <<<"$head"; then epcb+="$j"$'\n'; else esch+="$j"$'\n'; fi
    done <<<"$ej"
    use=${epcb:-$esch}
    if [ -n "$use" ]; then
      eparts=$(while read -r j; do [ -n "$j" ] && fetch "$j" | python3 "$DATA/easyeda_parts.py"; done <<<"$use")
      src="easyeda $( [ -n "$epcb" ] && echo pcb || echo schematic ) json"
      E_PANEL='PJ301|PJ-|THONK|POT|SW-|SW_|HDR|HEADER|IDC|LED|MHPS|KEY|CONN|JST|USB|MIDI|JACK|BUTTON|ENCODER|OLED|TEST|MOUNT|HOLE|LOGO|FIDUCIAL|TRIM|ARDUINO|TEENSY|DAISY|PICO|^NONE$'
      E_SMD='SOIC|SOT|SOD-|SMA_|SMB_|SMC_|-SMD|SMD_|SMD-|SOP|SSOP|TSSOP|QFN|QFP|MSOP|0201|0402|0603|0805|1206|1210|CASE-[AB]'
      E_IC='DIP|SIP-|TO-92|TO-220'
      E_THT='AXIAL|RADIAL|CAP-TH|-TH_|_TH_|DO-41|DO-35|1/[48]W'
      read smd tht thtic unkn <<<"$(awk -F'\t' -v P="$E_PANEL" -v S="$E_SMD" -v I="$E_IC" -v T="$E_THT" 'BEGIN{IGNORECASE=1}
        {k=$1} k~P{next} k~S{s++;next} k~I{i++;next} k~T{t++;next} {u++}
        END{print s+0, t+0, i+0, u+0}' <<<"$eparts")"
      unk=$(awk -F'\t' -v P="$E_PANEL" -v S="$E_SMD" -v I="$E_IC" -v T="$E_THT" 'BEGIN{IGNORECASE=1}
        $1!~P && $1!~S && $1!~I && $1!~T {print $1}' <<<"$eparts" | sort | uniq -c | awk '{print $2"x"$1}' | head -5 | tr '\n' ' ')
    fi
  fi

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
  # unclassified packages block the call only when they could change it: "both" (SMD with a
  # THT IC or 6+ THT passives) survives any extra part; SMD / THT verdicts might not.
  if [ -n "$unk" ]; then
    src="$src [unclassified: ${unk% }]"
    [ "$v" != "both" ] && { v=""; conf=Weak; }
  fi
  case "$src" in BOM*) [ -n "$v" ] && conf=Stated;; esac   # footprint sources (KiCad, EasyEDA) stay Strong

  printf '%s\t%s\t%s\t%s: smd=%s tht_passive=%s tht_transistor=%s tht_ic=%s (panel excluded) smd_ic=%s\t%s\t%s\n' \
    "$r" "$scope" "$v" "$src" "$smd" "$((tht - tq))" "$tq" "$thtic" "$ic" "$conf" "$DETECTOR_VERSION"
done
