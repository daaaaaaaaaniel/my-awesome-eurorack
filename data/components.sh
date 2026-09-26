#!/bin/bash
# Determine components = THT | SMD | both from hard evidence.
#
# Pass A, in order of preference:
#   1. KiCad footprint library names in .kicad_pcb  (v6 "(footprint " and v5 "(module ")
#   1b. EasyEDA JSON packages (when there is no counted KiCad board)
#   1c. Eagle .brd elements: <smd> vs <pad> per package is explicit (v15)
#   2. the BOM's footprint/package column
# Panel hardware NEVER disqualifies an SMD marking (CLAUDE.md): pots, jacks, switches,
# LEDs, headers and mounting holes are excluded from the THT tally entirely.
# With SMD present: any THT IC (DIP/SIP) -> both; else <=5 THT passives -> SMD, 6+ -> both.
# TO-92 / TO-220 parts (transistors, regulators) are counted and shown (tht_to=N) but never
# decide the verdict (user, 2026-09-26): any number of them beside SMD parts is still SMD.
#
# Input per line on stdin: "owner/repo", "owner/repo<TAB>module_dir", or
#   "owner/repo<TAB>module_dir<TAB>file_filter" - an extended regex (case-insensitive)
#   applied to the scoped file paths, for folders that hold several boards side by side
#   (Avalon CVMod8_V2: SMD and THT .kicad_pcb together -> run once per filter). Write the
#   root module as "." when a filter follows: bash read collapses an empty middle field.
#   Files are scoped to that ONE module by modulefiles.sh; without a dir the scope is the
#   repo's root module, never the whole repo, so a collection's boards are never pooled.
# Every file that contributed is named in the basis (files=N: a b c) so pooling is visible.
#
# Evidence is fetched at the inventory's pinned head_sha, never at the branch tip, so the
# tally always describes the commit the row records (v14). A fetch that fails is reported
# as "fetch failed", never as an absence of files.
# Output TSV: repo, module_scope, verdict, basis, confidence, detector_version
DETECTOR_VERSION=21

DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"

# panel hardware / mechanical — never counted as THT passives (KiCad footprint names)
PANEL='Potentiometer|LED_THT|LED_D|Connector|PinHeader|Pin_Header|Jack|Switch|Button|MountingHole|TestPoint|Fiducial|Screw|Socket|Terminal|Encoder|Display|Buttons|NetTie|Logo|Symbol|WEEE|ROHS|SLOT'
# Mechanical parts are panel-like: never counted (user, 2026-09-26). Heatsinks by name, plus
# data/known_parts.tsv - part numbers whose name says nothing (LCSC C286227 is a heatsink).
MECH='heat ?-?sink'"$(awk -F'\t' 'NR>1 && $2 ~ /^mechanical/ {printf "|%s", $1}' "$DATA/known_parts.tsv" 2>/dev/null)"
PANEL="$PANEL|$MECH"
# the same exclusion for BOM text, which says "LED 3mm", "Pot 100k", "trimmer" rather than
# footprint names (case-insensitive in the BOM path)
# v21: BOM lines carry descriptions - "switching diode" is not a switch
PANEL_BOM="${PANEL/Switch|/Switch([^i]|$)|}"'|(^|[^a-z])leds?([^a-z]|$)|(^|[^a-z])pots?([^a-z]|$)|trim(mer|pot)|header|(^|[^a-z])jacks?([^a-z]|$)|knob|standoff|nut([^a-z]|$)'
SMD_PKG='_SMD|Package_SO|SOIC|SOT-23|SOT23|SOT-?223|SOT-?89|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|0201|0402|0603|0805|1206'
# BOM text: chip sizes must stand alone ("0603", "R0603", "C_0805") - an LCSC code such
# as C120641 or a value like 1206 ohms must not read as a package
SMD_BOM='_SMD|(US|EU)_?[RCL]?(0201|0402|0603|0805|1206|1210|2012|3216)|SO-?0?(8|14|16|20|28)([^0-9]|$)|SSOP|(^|[^A-Za-z])SOP|CASE-?[A-E][_ -]?[0-9]|PANASONIC_[B-G]([^A-Za-z0-9]|$)|(^|[^0-9])(1608|2012|3216|3528|6032|7343)([^0-9]|$)|SOD-?(123|323|523|80|882|128)|MINIMELF|MELF|DO-?214|(^|[^A-Za-z])SM[ABC]([^A-Za-z]|$)|SOT-?(143|323|353|363|457|563|666)|SC-?70|SC-?88|DFN|WSON|D2?PAK|TO-?252|TO-?263|PowerPAK|(^|[^0-9A-Za-z])[RCL]?_?(1210|1812|2010|2512)([^0-9]|$)|L_pol_[0-9]{4}|Package_SO|SOIC|SO-?(8|14|16)([^0-9]|$)|SOT-?23|SOT-?223|SOT-?89|TSSOP|QFN|QFP|LQFP|TQFP|TQFN|TSOP|VSOP|VSSOP|MSOP|SMD|SMT|(^|[^0-9A-Za-z])[RCL]?_?(0201|0402|0603|0805|1206)([^0-9]|$)'
THT_PKG='_THT|DIP-|DIP_|TO-92|TO-220|DO-41|DO-35|Radial|Axial|7MM_RESISTOR|CAP-D'
# THT ICs: DIP / SIP packages only. Any one beside SMD parts makes the build "both". Counted
# from ALL footprints, so a socketed DIP (dropped by PANEL's "Socket") still counts.
THT_IC='DIP-|DIP_|SIP-|SIP_'
# TO-92 / TO-220 (and TO-3): shown as tht_to, excluded from passives and ICs alike.
THT_TO='TO-92|TO-220|TO-3([^0-9]|$)'
# BOM text spells these many ways: DIP8, DIP-8, DIP 8, PDIP8, DIL8, TO92, TO-220
THT_IC_BOM='P?DIP[ _-]?[0-9]|DIL[ _-]?[0-9]|SIP[ _-]?[0-9]'
THT_TO_BOM='TO-?92|TO-?220|TO-?3([^0-9]|$)'
THT_BOM="$THT_PKG"'|'"$THT_IC_BOM"'|'"$THT_TO_BOM"'|C_Disc|Disc_D[0-9]|through[- ]?hole|(^|[^a-z])THT([^a-z]|$)'
# v19 guard: lines that are not board parts whose package could flip the call (panel-side or
# package-neutral parts listed with R/C/L/D/Q/U designators)
NOTPART_BOM='pot|p09[0-9]|fader|slide|pta[0-9]|header|conn|europwr|euro_power|jack|switch|led|crystal|xtal|hc-?49|electrolytic|elko|cpol|c-polar|polarized|fuse|ferrite'

while IFS=$'\t' read -r r dir filt; do
  [ -n "$r" ] || continue
  key=$(echo "$r" | tr '/' '_'); f="$TREES/$key.txt"
  [ -s "$f" ] || { printf '%s\t%s\t\tno tree\tDeferred\t%s\n' "$r" "${dir:-.}" "$DETECTOR_VERSION"; continue; }
  mf=$(TREES="$TREES" bash "$DATA/modulefiles.sh" "$r" "$dir")
  scope=$(head -1 <<<"$mf" | cut -f2)
  files=$(tail -n +2 <<<"$mf")
  if [ -n "$filt" ]; then files=$(grep -iE "$filt" <<<"$files"); scope="$scope [$filt]"; fi
  # v21: BOM files recorded for this row outside its folder (data/html-boms.tsv, d 2026-09-26)
  xb=$(awk -F'\t' -v R="$r" -v D="${dir:-.}" 'NR>1 && $2==R && $3==D {print $4}' "$DATA/html-boms.tsv" 2>/dev/null)
  [ -n "$xb" ] && files=$(printf '%s\n%s\n' "$files" "$xb" | grep . | sort -u)
  # pinned commit from the inventory (CRLF-safe); the branch tip is only a fallback
  sha=$(awk -F'\t' -v R="$r" '$2==R{print $6}' "$INV" | tr -d '\r')
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV" | tr -d '\r')
  ref=${sha:-${br:-main}}
  # --fail: a missing file is an empty body, never a "404: Not Found" line fed to the parser
  fetch(){ curl -sS -m 40 --fail "https://raw.githubusercontent.com/$r/$ref/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$1")" 2>/dev/null; }

  smd=0; tht=0; ic=0; src=""; thtic=0; tq=0; used=""; nused=0; nfail=0; nempty=0; empties=""

  unkb=0
  # Revisions / fixed- copies of one board are never counted together (user, 2026-09-26, v16):
  # latest_files.py keeps the newest per board group; the rest are named in the basis and
  # generate.py queues them for review (a "v2" can be a different circuit).
  SUPF=$(mktemp)
  latest(){ local out; out=$(python3 "$DATA/latest_files.py"); grep '^#SUP' <<<"$out" | cut -f2 >> "$SUPF"; grep -v '^#SUP' <<<"$out"; }

  # --- 1. KiCad footprints ---
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    raw=$(fetch "$p") || { nfail=$((nfail+1)); continue; }
    parts=$(python3 "$DATA/kicad_parts.py" <<<"$raw")   # footprint<TAB>reference
    fps=$(cut -f1 <<<"$parts")
    [ -n "$fps" ] || { nempty=$((nempty+1)); empties="$empties${empties:+, }$(basename "$p") ($(wc -c <<<"$raw") bytes)"; continue; }
    src="kicad footprints"; nused=$((nused+1)); used="$used${used:+, }$(basename "$p")"
    keep=$(echo "$fps" | grep -vE "$PANEL")
    smd=$((smd + $(echo "$keep" | grep -cE "$SMD_PKG") ))
    tht=$((tht + $(echo "$keep" | grep -E "$THT_PKG" | grep -vE "$THT_IC" | grep -cvE "$THT_TO") ))
    tq=$((tq + $(echo "$fps" | grep -cE "$THT_TO") ))
    thtic=$((thtic + $(echo "$fps" | grep -cE "$THT_IC") ))
    ic=$((ic  + $(echo "$fps"  | grep -cE 'Package_SO|SOIC|TSSOP|QFN|QFP') ))
  done < <(grep -iE '\.kicad_pcb$' <<<"$files" | latest)

  # A KiCad file with no counted parts (e.g. a panel-only .kicad_pcb) does not hide an
  # EasyEDA circuit: fall through (Testbild-synth/headphone).
  [ "$src" = "kicad footprints" ] && [ $((smd + tht + thtic)) -eq 0 ] && { src=""; used=""; nused=0; }
  # --- 1b. EasyEDA JSON (no KiCad) ---
  # PCB JSON preferred (docType 3); schematic JSON only when no PCB JSON exists, so parts are
  # never counted twice. easyeda_parts.py collapses multi-unit parts by designator.
  # A package that is none of panel / SMD / THT leaves the call unmade (Weak -> blank).
  unk=""
  if [ -z "$src" ]; then
    ej=$(grep -iE '\.json$' <<<"$files" | grep -viE 'package\.json|\.vscode|tsconfig|manifest' | head -8)
    epcb=""; esch=""
    while IFS= read -r j; do
      [ -n "$j" ] || continue
      head=$(fetch "$j" | head -c 400) || { nfail=$((nfail+1)); continue; }
      grep -q 'editorVersion' <<<"$head" || continue
      if grep -qE '"docType": ?"?3' <<<"$head"; then epcb+="$j"$'\n'; else esch+="$j"$'\n'; fi
    done <<<"$ej"
    use=${epcb:-$esch}
    if [ -n "$use" ]; then
      eparts=$(while IFS= read -r j; do [ -n "$j" ] && fetch "$j" | python3 "$DATA/easyeda_parts.py"; done <<<"$use")
      src="easyeda $( [ -n "$epcb" ] && echo pcb || echo schematic ) json"
      nused=$(grep -c . <<<"$use"); used=$(grep . <<<"$use" | xargs -d '\n' -n1 basename | paste -sd, - | sed 's/,/, /g')
      E_PANEL='PJ301|PJ-|THONK|POT|SW-|SW_|HDR|HEADER|IDC|LED|MHPS|KEY|CONN|JST|USB|MIDI|JACK|BUTTON|ENCODER|OLED|TEST|MOUNT|HOLE|LOGO|FIDUCIAL|TRIM|ARDUINO|TEENSY|DAISY|PICO|^NONE$|'"$MECH"''
      E_SMD='SOIC|SOT|SOD-|SMA_|SMB_|SMC_|-SMD|SMD_|SMD-|SOP|SSOP|TSSOP|QFN|QFP|MSOP|0201|0402|0603|0805|1206|1210|CASE-[AB]'
      E_IC='DIP|SIP-'
      E_TO='TO-?92|TO-?220|TO-?3([^0-9]|$)'
      E_THT='AXIAL|RADIAL|CAP-TH|-TH_|_TH_|DO-41|DO-35|1/[48]W'
      read smd tht thtic tq unkn <<<"$(awk -F'\t' -v P="$E_PANEL" -v S="$E_SMD" -v I="$E_IC" -v O="$E_TO" -v T="$E_THT" 'BEGIN{P=tolower(P);S=tolower(S);I=tolower(I);O=tolower(O);T=tolower(T)}
        {k=tolower($1)} k~P{next} k~S{s++;next} k~I{i++;next} k~O{q++;next} k~T{t++;next} {u++}
        END{print s+0, t+0, i+0, q+0, u+0}' <<<"$eparts")"
      unk=$(awk -F'\t' -v P="$E_PANEL" -v S="$E_SMD" -v I="$E_IC" -v O="$E_TO" -v T="$E_THT" 'BEGIN{P=tolower(P);S=tolower(S);I=tolower(I);O=tolower(O);T=tolower(T)}
        {k=tolower($1)} k!~P && k!~S && k!~I && k!~O && k!~T {print $1}' <<<"$eparts" | sort | uniq -c | awk '{print $2"x"$1}' | head -5 | tr '\n' ' ')
    fi
  fi

  # --- 1c. Eagle .brd (no KiCad, no EasyEDA) ---
  # eagle_parts.py prints library:package<TAB>ref<TAB>smd|tht|none per placed part; the
  # mounting type comes from the package's own <smd>/<pad> elements, not from its name.
  # Panel hardware is excluded by library/package name (Eagle spellings); THT ICs are the
  # (v20: bare pin-header package names such as SparkFun 1X03 / 2X05 are panel hardware too)
  # DIL/DIP/SIP packages; TO92/TO220/TO3 parts are reported as tht_to and never decide.
  if [ -z "$src" ]; then
    E2_PANEL='jack|pj3|thonk|con-|conn|connector|terminal|header|pinhd|:[0-9]+x[0-9]+|icsp|jst|usb|midi|switch|button|tact|pot|trim|alps|encoder|led|display|oled|lcd|mount|hole|logo|fiducial|testpoint|test-|frame|docu|symbol|standoff|screw|solderjumper|jumper|'"$MECH"''
    E2_IC='DIL|DIP|SIP|SIL'
    E2_TO='TO-?92|TO-?220|TO-?3([^0-9]|$)'
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      raw=$(fetch "$b") || { nfail=$((nfail+1)); continue; }
      eparts=$(python3 "$DATA/eagle_parts.py" <<<"$raw")
      [ -n "$eparts" ] || { nempty=$((nempty+1)); empties="$empties${empties:+, }$(basename "$b") (not XML or no elements, $(wc -c <<<"$raw") bytes)"; continue; }
      src="eagle packages"; nused=$((nused+1)); used="$used${used:+, }$(basename "$b")"
      read s1 t1 i1 q1 sic <<<"$(awk -F'\t' -v P="$E2_PANEL" -v I="$E2_IC" -v O="$E2_TO" 'BEGIN{P=tolower(P); I=tolower(I); O=tolower(O)}
        {k=tolower($1)} k ~ P {next}
        $3=="smd" { s++; if (k ~ /so[0-9]|soic|tssop|qfn|qfp|sot-?23|msop/) sic++; next }
        $3=="tht" { if (k ~ I) i++; else if (k ~ O) q++; else t++ }
        END{print s+0, t+0, i+0, q+0, sic+0}' <<<"$eparts")"
      smd=$((smd + s1)); tht=$((tht + t1)); tq=$((tq + q1)); thtic=$((thtic + i1)); ic=$((ic + sic))
    done < <(grep -iE '\.brd$' <<<"$files" | latest)
  fi

  # --- 1d. Interactive HTML BOM (iBOM), v21 (d 2026-09-26) ---
  # ibom_parts.py decodes pcbdata: every pad is "smd" or "th", explicit like Eagle. Panel
  # hardware is excluded by footprint name (KiCad and Eagle spellings), or by reference when
  # iBOM gives no name; THT ICs are DIP/DIL/SIP/SIL, counted before panel exclusion so a
  # socketed DIP still counts; TO-92/TO-220/TO-3 are tht_to and never decide.
  if [ -z "$src" ]; then
    I_PANEL="$PANEL"'|jack|pj-?3|thonk|conn|header|pinhd|pin_?socket|icsp|switch|button|tact|pot|trim|alps|fader|encoder|led|display|oled|lcd|mount|hole|logo|fiducial|test_?point|standoff|screw|jumper|:[0-9]+x[0-9]+|board_?conv|(^|[^0-9])(3296|3362|3386)[a-z0-9]|rd90[0-9]|rk0?9|rv0?9|pj-?[0-9]|sw_push|(^|[^a-z])sw_|eurorack_[0-9]+hp|hdsp|bar_?graph|solder_?pad|net_?tie|value:.*(led|jack|pot|switch|header)'
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      raw=$(fetch "$b") || { nfail=$((nfail+1)); continue; }
      iparts=$(python3 "$DATA/ibom_parts.py" <<<"$raw" 2>/dev/null)
      [ -n "$iparts" ] || continue          # not an iBOM: a plain HTML table or a web page
      src="ibom pads"; nused=$((nused+1)); used="$used${used:+, }$(basename "$b")"
      read s1 t1 i1 q1 sic <<<"$(awk -F'\t' -v P="$I_PANEL" 'BEGIN{P=tolower(P)}
        {k=tolower($1); r=$2}
        $3=="tht" && k ~ /(^|[^a-z])(dip|dil|sip|sil)[-_ ]?[0-9]/ { i++; next }
        k ~ P {next}
        r ~ /^(J|SW|S|RV|VR|LED|H|MH|TP|FID|JP|BAR|DS)[0-9]/ || r ~ /^REF\*/ {next}   # panel by reference, named or not
        (k=="" || k ~ /^value:/) && r ~ /^P[0-9]/ {next}
        $3=="smd" { s++; if (k ~ /so[-_]?[0-9]|soic|tssop|qfn|qfp|sot-?23|msop/) sic++; next }
        $3=="tht" { if (k ~ /to-?92|to-?220|to-?3([^0-9]|$)/) q++; else t++ }
        END{print s+0, t+0, i+0, q+0, sic+0}' <<<"$iparts")"
      smd=$((smd + s1)); tht=$((tht + t1)); tq=$((tq + q1)); thtic=$((thtic + i1)); ic=$((ic + sic))
    done < <(grep -iE '\.html?$' <<<"$files" | head -12 | latest)
  fi

  # --- 2. BOM fallback ---
  if [ -z "$src" ]; then
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      if [[ "${b,,}" =~ \.(xlsx|ods)$ ]]; then                    # v19: spreadsheet BOMs, first sheet
        tf=$(mktemp --suffix=".${b##*.}"); fetch "$b" > "$tf" || { nfail=$((nfail+1)); rm -f "$tf"; continue; }
        body=$(python3 "$DATA/xl2tsv.py" "$tf" 2>/dev/null); rm -f "$tf"
      elif [[ "${b,,}" =~ \.html?$ ]]; then                    # v21: HTML table BOMs (KiCad exports)
        body=$(fetch "$b" | python3 "$DATA/html2tsv.py" 2>/dev/null)
      else body=$(fetch "$b") || { nfail=$((nfail+1)); continue; }; fi
      [ -n "$body" ] || continue
      src="BOM"; nused=$((nused+1)); used="$used${used:+, }$b"
      # count PARTS, not BOM lines: qty column, else designator count (bom_parts.py)
      rows=$(python3 "$DATA/bom_parts.py" <<<"$body")         # qty<TAB>refs<TAB>text
      # case-insensitive via tolower() on both sides: IGNORECASE is gawk-only and mawk (the
      # cloud container's awk) ignores it silently. Designators (Q) stay case-sensitive.
      sumq(){ awk -F'\t' -v P="$1" -v N="$2" -v Q="$3" 'BEGIN{P=tolower(P); N=tolower(N)}
               tolower($3) ~ P && (N=="" || tolower($3) !~ N) && (Q=="" || $2 ~ Q) {s+=$1} END{print s+0}' <<<"$rows"; }
      smd=$((smd + $(sumq "$SMD_BOM" "$PANEL_BOM") ))
      tht=$((tht + $(awk -F'\t' -v P="$THT_BOM" -v N="$PANEL_BOM" -v I="$THT_IC_BOM" -v O="$THT_TO_BOM" 'BEGIN{P=tolower(P); N=tolower(N); I=tolower(I); O=tolower(O)} {l=tolower($3)} l ~ P && l !~ N && l !~ I && l !~ O {s+=$1} END{print s+0}' <<<"$rows") ))
      tq=$((tq + $(sumq "$THT_TO_BOM" "$PANEL_BOM") ))
      thtic=$((thtic + $(sumq "$THT_IC_BOM" '') ))
      ic=$((ic  + $(sumq 'SOIC|TSSOP|QFN|QFP' '') ))
      # v19: parts (R/C/L/D/Q/U/IC designators) whose line matches no SMD, THT or panel pattern
      unkb=$((unkb + $(awk -F'\t' -v G="$NOTPART_BOM" -v S="$SMD_BOM" -v T="$THT_BOM" -v N="$PANEL_BOM" 'BEGIN{S=tolower(S); T=tolower(T); N=tolower(N); G=tolower(G)}
               {l=tolower($3)} $2 ~ /(^|[ ,;])(R|C|L|D|Q|U|IC)[0-9]/ && l !~ S && l !~ T && l !~ N && l !~ G {s+=$1} END{print s+0}' <<<"$rows") ))
    done < <({ grep -iE '(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv|xlsx|ods|html?)$' <<<"$files"; grep -iE '\.html?$' <<<"$xb"; } | grep . | sort -u | latest)
  fi

  if [ -z "$src" ]; then
    if [ "$nfail" -gt 0 ]; then
      printf '%s\t%s\t\tfetch failed for %s file(s) at %s - re-run, do not read as absence\tDeferred\t%s\n' "$r" "$scope" "$nfail" "$ref" "$DETECTOR_VERSION"
    elif [ "$nempty" -gt 0 ]; then
      printf '%s\t%s\t\t%s .kicad_pcb fetched but held no footprints (LFS stub or empty board?): %s\tDeferred\t%s\n' "$r" "$scope" "$nempty" "$empties" "$DETECTOR_VERSION"
    else
      printf '%s\t%s\t\tno .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM or machine-readable BOM in scope\tDeferred\t%s\n' "$r" "$scope" "$DETECTOR_VERSION"
    fi
    continue
  fi

  [ -s "$SUPF" ] && src="$src [superseded, not counted: $(xargs -r -d '\n' -n1 basename < "$SUPF" | sort -u | paste -sd, - | sed 's/,/, /g')]"
  rm -f "$SUPF"
  # --- verdict (user, 2026-09-26, revised the same day) ---
  # SMD present: any THT IC (DIP/SIP) -> both; else <=5 THT passives -> SMD, 6+ -> both.
  # TO-92/TO-220 parts never decide. No SMD at all -> THT. Panel hardware never counts.
  conf=Strong
  if [ "$smd" -gt 0 ] && [ "$thtic" -gt 0 ]; then v=both
  elif [ "$smd" -gt 0 ] && [ "$tht" -le 5 ]; then v=SMD
  elif [ "$smd" -gt 0 ]; then v=both
  elif [ "$tht" -gt 0 ] || [ "$thtic" -gt 0 ] || [ "$tq" -gt 0 ]; then v=THT
  else v=""; conf=Deferred; fi
  # unclassified packages block the call only when they could change it: "both" (SMD with a
  # THT IC or 6+ THT passives) survives any extra part, and so does "SMD" while even
  # counting every unknown as a THT passive stays within the 5 limit (the unknown cannot
  # be a DIP/SIP, which E_IC would have matched by name). Otherwise blank, Weak.
  if [ -n "$unk" ]; then
    src="$src [unclassified: ${unk% }]"
    if [ "$v" = "SMD" ] && [ $((tht + ${unkn:-0})) -le 5 ]; then :; elif [ "$v" != "both" ]; then v=""; conf=Weak; fi
  fi
  # v19: a BOM that names no package for some parts cannot settle a call those parts could change:
  # THT (they might be SMD) or SMD beyond the 5-passive limit. "both" survives. Blank, Weak.
  if [ "${unkb:-0}" -gt 0 ] && [ "${src%% *}" = "BOM" ]; then
    src="$src [no package named for $unkb part(s)]"
    if [ "$v" = "THT" ] || { [ "$v" = "SMD" ] && [ $((tht + unkb)) -gt 5 ]; }; then v=""; conf=Weak; fi
  fi
  case "$src" in BOM*) [ -n "$v" ] && conf=Stated;; esac   # footprint sources (KiCad, EasyEDA, Eagle) stay Strong
  failnote=""; [ "$nfail" -gt 0 ] && failnote="; fetch failed for $nfail other file(s)"

  printf '%s\t%s\t%s\t%s (files=%s: %s): smd=%s tht_passive=%s tht_to=%s tht_ic=%s (panel excluded) smd_ic=%s%s\t%s\t%s\n' \
    "$r" "$scope" "$v" "$src" "$nused" "$used" "$smd" "$tht" "$tq" "$thtic" "$ic" "$failnote" "$conf" "$DETECTOR_VERSION"
done
