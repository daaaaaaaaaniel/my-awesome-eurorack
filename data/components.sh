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
#   An optional 4th column lists extra repo paths, '|'-separated, counted with the scope's files
#   whatever folder they are in: sub-boards pooled from sibling folders (rerun_rows.py passes the
#   ones a row recorded). The filter does not apply to them; give a non-empty filter ('.') with it,
#   since bash read collapses empty TAB fields.
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
DETECTOR_VERSION=27
# basename per line; xargs -d is GNU-only and fails silently on macOS (2026-10-23)
bn(){ while IFS= read -r l; do [ -n "$l" ] && printf '%s\n' "${l##*/}"; done; }
# PANEL_COUNT=1 (prepared 2026-09-28 for d's go, website note 0045): append " panel=N" to the
# tally - panel components (jacks, pots, switches, LEDs, headers, sockets, dev-board modules) on
# footprint sources (KiCad, EasyEDA, Eagle, iBOM). A recorded count ONLY: it never enters the
# verdict (the v22 panel-only rule keeps using $pan). No panel= on BOM or gerber rows (not counted,
# never panel=0 for unknown). Mechanical parts (heatsinks, known_parts.tsv) and non-parts (mounting
# holes, fiducials, logos, test points, net ties, slots) are not components. On d's go: make this
# the default, bump to v24, re-run every row, check no components verdict moved.
PANEL_COUNT=${PANEL_COUNT:-1}   # v24 (d 2026-09-28 06:38): on by default

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
# v27: the KiCad, EasyEDA, Eagle and iBOM paths classify parts with data/part_class.py; PANEL and the package lists
# below are now used by the BOM path only (PANEL_BOM, SMD_BOM, THT_BOM ...).
# A faceplate PCB, by name (the CPL audit's test): panel / faceplate / frontplate / plate in the file name, or a folder
# ending in "panel". Skipped only when it holds no circuit parts (a circuit board named "Panel" still counts).
FACEPLATE='(^|/)[^/]*(panel|faceplate|frontplate|front_plate|plate)[^/]*$|panel/[^/]*$'
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

while IFS=$'\t' read -r r dir filt extra; do
  [ -n "$r" ] || continue
  key=$(echo "$r" | tr '/' '_'); f="$TREES/$key.txt"
  [ -s "$f" ] || { printf '%s\t%s\t\tno tree\tDeferred\t%s\n' "$r" "${dir:-.}" "$DETECTOR_VERSION"; continue; }
  mf=$(TREES="$TREES" bash "$DATA/modulefiles.sh" "$r" "$dir")
  scope=$(head -1 <<<"$mf" | cut -f2)
  files=$(tail -n +2 <<<"$mf")
  allfiles=$files   # the whole module scope, before any pin filter (the backup rule below looks here)
  if [ -n "$filt" ]; then files=$(grep -iE "$filt" <<<"$files"); scope="$scope [$filt]"; fi
  # v23: a .kicad_pcb under 100 bytes is an empty board, not a PCB (d, 2026-09-28). kicad_stubs.sh
  # has already removed them from the trees; name the ones in this scope so the basis says why
  # there is no board.
  stubs=$(awk -F'\t' -v R="$r" 'NR>1 && $1==R {print $3}' "$DATA/kicad-stubs.tsv" 2>/dev/null)
  stubnote=""
  if [ -n "$stubs" ]; then
    sd=$(head -1 <<<"$mf" | cut -f2)
    if [ "$sd" = "." ]; then
      oth=$(TREES="$TREES" bash "$DATA/moduledirs.sh" "$r" | sed -E 's/^ *[0-9]+ //' | grep -vxF '.')
      stubs=$(OTHERS="$oth" awk 'BEGIN{n=split(ENVIRON["OTHERS"],o,"\n")} {for(i=1;i<=n;i++) if(o[i]!="" && index($0,o[i]"/")==1) next; print}' <<<"$stubs")
    else
      stubs=$(D="$sd/" awk 'index($0,ENVIRON["D"])==1' <<<"$stubs")
    fi
    [ -n "$filt" ] && [ -n "$stubs" ] && stubs=$(grep -iE "$filt" <<<"$stubs")
    [ -n "$stubs" ] && stubnote="; $(grep -c . <<<"$stubs") .kicad_pcb under 100 bytes treated as absent (empty KiCad board): $(bn <<<"$stubs" | paste -sd, - | sed 's/,/, /g')"
  fi
  # v24 also: the iBOM / Eagle "not a part" filters matched bare "solder", which hit KiCad *_HandSolder
  # footprints (every hand-solder 0805 R/C: 909 Kick 131 SMD read as 31) - now solder jumper/bridge/pad/point only.
  # v24: a solder-stencil copy of a board is not a board (d 2026-09-28 06:38, Addatone: "don't count the
  # stencil") - dropped from the files, named in the basis. Applied after the pin filter, so pinned rows too.
  stencils=$(grep -iE '(^|/)[^/]*stencil[^/]*$' <<<"$files")
  stencilnote=""
  if [ -n "$stencils" ]; then
    files=$(grep -viE '(^|/)[^/]*stencil[^/]*$' <<<"$files")
    stencilnote="; stencil copy not counted: $(bn <<<"$stencils" | paste -sd, - | sed 's/,/, /g')"
  fi
  # v21: BOM files recorded for this row outside its folder (data/html-boms.tsv, d 2026-09-26)
  xb=$(awk -F'\t' -v R="$r" -v D="${dir:-.}" 'NR>1 && $2==R && $3==D {print $4}' "$DATA/html-boms.tsv" 2>/dev/null)
  [ -n "$xb" ] && files=$(printf '%s\n%s\n' "$files" "$xb" | grep . | sort -u)
  [ -n "$extra" ] && files=$(printf '%s\n%s\n' "$files" "$(tr '|' '\n' <<<"$extra")" | grep . | sort -u)
  # v24: backup copies (a folder named *backup*: KiCad's fjol-backups/<date>/, KiCAD9-BACKUP/) are skipped ONLY
  # when the board they back up - a file of the same name outside any backup folder - is in the module (d
  # 2026-09-28 06:55: "check that the backup isn't the only board"). A backup with no current counterpart counts.
  BK='(^|/)[^/]*backups?[^/]*/'
  bks=$(grep -iE "$BK" <<<"$files")
  backupnote=""
  if [ -n "$bks" ]; then
    cur=$(printf '%s\n%s\n' "$allfiles" "$files" | grep . | grep -viE "$BK" | bn 2>/dev/null | sort -u)
    skip=""; kept=""
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      if grep -qxF "$(basename "$b")" <<<"$cur"; then skip+="$b"$'\n'; else kept+="$(basename "$b"), "; fi
    done <<<"$bks"
    if [ -n "$skip" ]; then
      files=$(grep -vxF -f <(printf '%s' "$skip") <<<"$files")
      backupnote="; backup copy not counted (current board present): $(grep . <<<"$skip" | awk '{n=split($0,a,"/"); printf "%s%s/%s", (NR>1?", ":""), a[n-1], a[n]}')"
    fi
    [ -n "$kept" ] && backupnote="$backupnote; backup counted - no current board of that name: ${kept%, }"
  fi
  # pinned commit from the inventory (CRLF-safe); the branch tip is only a fallback
  sha=$(awk -F'\t' -v R="$r" '$2==R{print $6}' "$INV" | tr -d '\r')
  br=$(awk -F'\t' -v R="$r" '$2==R{print $7}' "$INV" | tr -d '\r')
  ref=${sha:-${br:-main}}
  # --fail: a missing file is an empty body, never a "404: Not Found" line fed to the parser
  fetch(){ curl -sS -m 40 --fail "https://raw.githubusercontent.com/$r/$ref/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$1")" 2>/dev/null; }

  smd=0; tht=0; ic=0; src=""; thtic=0; tq=0; used=""; nused=0; nfail=0; nempty=0; empties=""
  unkn=0; unk=""; faces=""; autonote=""; kheld=""   # v27
  pcnt=0            # PANEL_COUNT: panel components, recorded only (never a verdict input)
  pan=0; pansmd=0   # v22: panel parts seen, and how many of them are SMD (footprint sources only)

  unkb=0
  # Revisions / fixed- copies of one board are never counted together (user, 2026-09-26, v16):
  # latest_files.py keeps the newest per board group; the rest are named in the basis and
  # generate.py queues them for review (a "v2" can be a different circuit).
  SUPF=$(mktemp)
  latest(){ local out; out=$(python3 "$DATA/latest_files.py"); grep '^#SUP' <<<"$out" | cut -f2 >> "$SUPF"; grep -v '^#SUP' <<<"$out"; }

  # --- 1. KiCad footprints ---
  # v27: kicad_parts.py reads each footprint's mounting from its pads; part_class.py classifies every part (the same
  # classifier for KiCad, EasyEDA, Eagle and iBOM). A faceplate PCB - named panel / faceplate / frontplate / plate, or
  # in a folder ending "panel" (the CPL audit's test) - holding no circuit parts is not a board: not counted, named in
  # the basis (caseyjholmes ADSR-Panel.kicad_pcb). A KiCad autosave copy (_autosave-*.kicad_pcb) is never counted
  # beside a real board (p247, p300).
  kpcbs=$(grep -iE '\.kicad_pcb$' <<<"$files")
  autos=$(grep -iE '(^|/)_autosave-[^/]*$' <<<"$kpcbs")
  if [ -n "$autos" ] && grep -viE '(^|/)_autosave-[^/]*$' <<<"$kpcbs" | grep -q .; then
    kpcbs=$(grep -viE '(^|/)_autosave-[^/]*$' <<<"$kpcbs")
    autonote="; autosave copy not counted: $(bn <<<"$autos" | paste -sd, - | sed 's/,/, /g')"
  fi
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    raw=$(fetch "$p") || { nfail=$((nfail+1)); continue; }
    parts=$(python3 "$DATA/kicad_parts.py" <<<"$raw")   # footprint, reference, mount, pads, value
    [ -n "$parts" ] || { nempty=$((nempty+1)); empties="$empties${empties:+, }$(basename "$p") ($(wc -c <<<"$raw") bytes)"; continue; }
    kr=$(python3 "$DATA/part_class.py" <<<"$parts"); read s1 t1 i1 q1 sic p1 ps1 u1 <<<"$(cut -f1 <<<"$kr")"
    if [ $((s1 + t1 + i1 + q1)) -eq 0 ] && grep -qiE "$FACEPLATE" <<<"$p"; then faces="$faces${faces:+, }$(basename "$p")"; continue; fi
    src="kicad footprints"; nused=$((nused+1)); used="$used${used:+, }$(basename "$p")"
    smd=$((smd + s1)); tht=$((tht + t1)); thtic=$((thtic + i1)); tq=$((tq + q1)); ic=$((ic + sic))
    pan=$((pan + p1)); pansmd=$((pansmd + ps1)); pcnt=$((pcnt + p1)); unkn=$((unkn + u1)); unk="$unk$(cut -s -f2 <<<"$kr") "
  done < <(latest <<<"$kpcbs")

  # A KiCad board with no circuit parts (panel parts only) does not hide a circuit drawn in another footprint source
  # (fc6e6e5, Testbild-synth/headphone: a KiCad panel beside an EasyEDA circuit): set it aside and try the others.
  # v27: if none of them decides, the KiCad board does - verified no SMD parts -> THT (v22). Before v27 it was dropped
  # for good: the basis said "no .kicad_pcb" and the v22 rule never fired for a KiCad board (p95, p251, p69).
  kheld=""
  if [ "$src" = "kicad footprints" ] && [ $((smd + tht + thtic + tq)) -eq 0 ]; then
    kheld="$used|$nused|$pan|$pansmd|$pcnt"; src=""; used=""; nused=0; pan=0; pansmd=0; pcnt=0
  fi
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
    # v26 (d 2026-10-23, Voxmachina): EasyEDA exports often ship zipped (Cha Cha - VCLFO/EasyEDA/
    # main_board_project.zip holds 1-PCB_PCB.json). With no loose EasyEDA JSON, open the scope's zips;
    # members are recorded as "zip!member" and read from the extracted copy.
    ezd=""
    if [ -z "$epcb$esch" ]; then
      ezd=$(mktemp -d); zi=0
      while IFS= read -r z; do
        [ -n "$z" ] || continue; zi=$((zi+1))
        fetch "$z" > "$ezd/$zi.zip" || { nfail=$((nfail+1)); continue; }
        # Python zipfile, not the unzip binary (the cloud container may lack it; every other script uses zipfile).
        # One level of nesting: Mak Mak's EasyEDA/main_pcb.zip holds 'VCA MAIN_<id>.zip'.
        python3 "$DATA/zip_json.py" "$ezd/$zi.zip" "$ezd/$zi" 2>/dev/null
        while IFS= read -r m; do
          head=$(head -c 400 "$ezd/$zi/$m")
          grep -q 'editorVersion' <<<"$head" || continue
          if grep -qE '"docType": ?"?3' <<<"$head"; then epcb+="$z!$m"$'\n'; else esch+="$z!$m"$'\n'; fi
        done < <(cd "$ezd/$zi" && find . -type f -iname '*.json' | sed 's|^\./||' | sort)
      done < <(grep -iE '\.zip$' <<<"$files" | head -6)
    fi
    use=${epcb:-$esch}
    [ -z "$use" ] && [ -n "$ezd" ] && rm -rf "$ezd"
    if [ -n "$use" ]; then
      eparts=$(while IFS= read -r j; do
        [ -n "$j" ] || continue
        if [[ "$j" == *.zip!* ]]; then
          zn=$(grep -nxF "${j%%!*}" < <(grep -iE '\.zip$' <<<"$files" | head -6) | head -1 | cut -d: -f1)
          python3 "$DATA/easyeda_parts.py" < "$ezd/$zn/${j#*!}"
        else fetch "$j" | python3 "$DATA/easyeda_parts.py"; fi
      done <<<"$use")
      [ -n "$ezd" ] && rm -rf "$ezd"
      src="easyeda $( [ -n "$epcb" ] && echo pcb || echo schematic ) json$( [ -n "$ezd" ] && echo ' (zipped)' )"
      nused=$(grep -c . <<<"$use"); used=$(grep . <<<"$use" | while IFS= read -r j; do
        if [[ "$j" == *.zip!* ]]; then z=${j%%!*}; echo "${z##*/}!${j#*!}"; else echo "${j##*/}"; fi; done | paste -sd, - | sed 's/,/, /g')
      kr=$(python3 "$DATA/part_class.py" <<<"$eparts")   # v27: the shared classifier
      read smd tht thtic tq ic pcnt pansmd unkn <<<"$(cut -f1 <<<"$kr")"
      unk=$(cut -s -f2 <<<"$kr")
    fi
  fi

  # --- 1c. Eagle .brd (no KiCad, no EasyEDA) ---
  # eagle_parts.py prints library:package<TAB>ref<TAB>smd|tht|none<TAB>pads per placed part; the
  # mounting type comes from the package's own <smd>/<pad> elements, not from its name.
  # v27: classified by part_class.py like every footprint source (before v27 Eagle had its own panel list, E2_PANEL,
  # which missed faders, PJ_301 jacks, 3386 trimmers, power headers, Teensy boards and wire pads, and read the
  # Teensy's 'DIL' library name as a DIP chip).
  if [ -z "$src" ]; then
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      raw=$(fetch "$b") || { nfail=$((nfail+1)); continue; }
      eparts=$(python3 "$DATA/eagle_parts.py" <<<"$raw")
      [ -n "$eparts" ] || { nempty=$((nempty+1)); empties="$empties${empties:+, }$(basename "$b") (not XML or no elements, $(wc -c <<<"$raw") bytes)"; continue; }
      kr=$(python3 "$DATA/part_class.py" <<<"$eparts"); read s1 t1 i1 q1 sic p1 ps1 u1 <<<"$(cut -f1 <<<"$kr")"   # v27
      if [ $((s1 + t1 + i1 + q1)) -eq 0 ] && grep -qiE "$FACEPLATE" <<<"$b"; then faces="$faces${faces:+, }$(basename "$b")"; continue; fi
      src="eagle packages"; nused=$((nused+1)); used="$used${used:+, }$(basename "$b")"
      smd=$((smd + s1)); tht=$((tht + t1)); tq=$((tq + q1)); thtic=$((thtic + i1)); ic=$((ic + sic)); pan=$((pan + p1)); pansmd=$((pansmd + ps1)); pcnt=$((pcnt + p1))
      unkn=$((unkn + u1)); unk="$unk$(cut -s -f2 <<<"$kr") "
    done < <(grep -iE '\.brd$' <<<"$files" | latest)
  fi

  # --- 1d. Interactive HTML BOM (iBOM), v21 (d 2026-09-26) ---
  # ibom_parts.py decodes pcbdata: every pad is "smd" or "th", explicit like Eagle. v27: classified by part_class.py
  # (its panel test already used names plus references, as iBOM had since v21).
  if [ -z "$src" ]; then
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      raw=$(fetch "$b") || { nfail=$((nfail+1)); continue; }
      iparts=$(python3 "$DATA/ibom_parts.py" <<<"$raw" 2>/dev/null)
      [ -n "$iparts" ] || continue          # not an iBOM: a plain HTML table or a web page
      src="ibom pads"; nused=$((nused+1)); used="$used${used:+, }$(basename "$b")"
      kr=$(python3 "$DATA/part_class.py" <<<"$iparts"); read s1 t1 i1 q1 sic p1 ps1 u1 <<<"$(cut -f1 <<<"$kr")"   # v27
      smd=$((smd + s1)); tht=$((tht + t1)); tq=$((tq + q1)); thtic=$((thtic + i1)); ic=$((ic + sic)); pan=$((pan + p1)); pansmd=$((pansmd + ps1)); pcnt=$((pcnt + p1))
      unkn=$((unkn + u1)); unk="$unk$(cut -s -f2 <<<"$kr") "
    done < <(grep -iE '\.html?$' <<<"$files" | head -12 | latest)
  fi

  # v27: no EasyEDA / Eagle / iBOM source decided - the KiCad board set aside above decides (panel parts only)
  if [ -z "$src" ] && [ -n "$kheld" ]; then
    IFS='|' read -r used nused pan pansmd pcnt <<<"$kheld"; src="kicad footprints"; smd=0; tht=0; thtic=0; tq=0; ic=0
  fi

  # --- 2. BOM fallback ---
  if [ -z "$src" ]; then
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      if [[ "${b,,}" =~ \.(xlsx|ods)$ ]]; then                    # v19: spreadsheet BOMs, first sheet
        td=$(mktemp -d); tf="$td/bom.${b##*.}"   # not mktemp --suffix: GNU-only, fails on macOS
        fetch "$b" > "$tf" || { nfail=$((nfail+1)); rm -rf "$td"; continue; }
        # a conversion that crashes (openpyxl missing on macOS Homebrew python, 2026-10-23) is a failure, not an absence
        body=$(python3 "$DATA/xl2tsv.py" "$tf" 2>/dev/null) || { nfail=$((nfail+1)); rm -rf "$td"; continue; }; rm -rf "$td"
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
    # v25: every BOM file recorded in html-boms.tsv counts, not only HTML ones - Mutable Instruments names its BOM
    # after the module (plaits/hardware_design/Plaits.xlsx; d 2026-09-28 07:20)
    done < <({ grep -iE '(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv|xlsx|ods|html?)$' <<<"$files"; grep -iE '\.(html?|csv|tsv|xlsx|ods)$' <<<"$xb"; } | grep . | sort -u | latest)
  fi

  # --- 3. Gerbers (v22, d 2026-09-26 16:15/16:23), last resort ---
  # gerber_nosmd.py: stencil pads that are not on a drilled hole are SMD pads. None, with a paste
  # layer and component holes present -> no SMD parts -> THT. SMD pads found -> SMD or both,
  # which gerbers cannot tell apart: the row stays blank and the basis says so.
  gnote=""
  # v26: never fall back to gerbers past a file that could not be fetched or converted - the better
  # source might have decided the row (an .ods BOM with no soffice on macOS read THT from gerbers, 2026-10-23)
  if [ -z "$src" ] && [ "$nfail" -eq 0 ]; then
    gf=$( { grep -iE '(\.gtp|\.gbp|\.crm|\.crs|\.tcream|\.bcream)$|paste[^/]*\.(gbr|ger|pho|gtp|gbp)$' <<<"$files"
            grep -iE '\.(drl|xln|exc)$|(^|/)[^/]*(drill|pth)[^/]*\.txt$' <<<"$files"
            grep -iE '\.zip$' <<<"$files" | grep -viE -- '-backups/|firmware|software|source|code|lib|librar|3d|step|stl' | head -6; } | grep . | sort -u)
    if [ -n "$gf" ]; then
      gd=$(mktemp -d); gi=0
      while IFS= read -r g; do gi=$((gi+1)); fetch "$g" > "$gd/$gi-$(basename "$g" | tr -d '\n' | tr -c 'A-Za-z0-9._-' _)" || nfail=$((nfail+1)); done <<<"$gf"
      gres=$(python3 "$DATA/gerber_nosmd.py" "$gd"/* 2>/dev/null); rm -rf "$gd"
      read gp gpads gon gsmd gcomp gdr <<<"$(sed -E 's/[a-z_]+=//g' <<<"$gres")"
      if [ "${gp:-0}" -ge 1 ] && [ "${gcomp:-0}" -ge 1 ] && [ "${gsmd:-1}" -eq 0 ]; then
        src="gerber paste+drill [no SMD pads: ${gpads} paste pads, ${gon} of them on drilled holes; ${gcomp} component holes]"
        nused=$(grep -c . <<<"$gf"); used=$(bn <<<"$gf" | paste -sd, - | sed 's/,/, /g'); pan=1
      elif [ "${gsmd:-0}" -gt 0 ]; then gnote="; gerbers show ${gsmd} SMD pads (SMD or both - gerbers cannot tell which)"
      elif [ "${gp:-0}" -eq 0 ]; then gnote="; gerbers have no paste layer (proves nothing)"
      fi
    fi
  fi

  if [ -z "$src" ]; then
    if [ "$nfail" -gt 0 ]; then
      printf '%s\t%s\t\tfetch failed for %s file(s) at %s - re-run, do not read as absence\tDeferred\t%s\n' "$r" "$scope" "$nfail" "$ref" "$DETECTOR_VERSION"
    elif [ "$nempty" -gt 0 ]; then
      printf '%s\t%s\t\t%s .kicad_pcb fetched but held no footprints (LFS stub or empty board?): %s\tDeferred\t%s\n' "$r" "$scope" "$nempty" "$empties" "$DETECTOR_VERSION"
    else
      printf '%s\t%s\t\tno .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope%s%s\tDeferred\t%s\n' "$r" "$scope" "$gnote" "$stubnote" "$DETECTOR_VERSION"
    fi
    continue
  fi

  [ "$smd" -eq 0 ] && [ "$pansmd" -gt 0 ] && [ $((tht + thtic + tq)) -gt 0 ] && src="$src [SMD only in panel parts: $pansmd]"   # v27
  [ -s "$SUPF" ] && src="$src [superseded, not counted: $(bn < "$SUPF" | sort -u | paste -sd, - | sed 's/,/, /g')]"
  rm -f "$SUPF"
  # --- verdict (user, 2026-09-26, revised the same day) ---
  # SMD present: any THT IC (DIP/SIP) -> both; else <=5 THT passives -> SMD, 6+ -> both.
  # TO-92/TO-220 parts never decide. No SMD at all -> THT. Panel hardware never counts.
  conf=Strong
  # v27: an SMD panel part (SMD LED, SMD switch) needs SMD soldering too - "SMD present" counts it (pansmd), the smd
  # count does not. The v22 rules below already refused THT for a panel-only board with SMD panel parts.
  sp=$((smd + pansmd))
  if [ "$sp" -gt 0 ] && [ "$thtic" -gt 0 ]; then v=both
  elif [ "$sp" -gt 0 ] && [ "$tht" -gt 5 ]; then v=both
  elif [ "$sp" -gt 0 ] && [ $((smd + tht + tq)) -gt 0 ]; then v=SMD   # SMD panel parts alone fall to the v22 rules below
  # (each of the above is said in the basis when only panel parts were SMD)
  elif [ "$tht" -gt 0 ] || [ "$thtic" -gt 0 ] || [ "$tq" -gt 0 ]; then v=THT
  # v22 (d 2026-09-26 16:23): verified to have no SMD parts -> THT, even when every part is panel
  # hardware (passive mults, attenuators, bus boards). Footprint sources only: a BOM that parses
  # to nothing proves nothing (DrJ3RK's shared BOMs.txt reads 0 parts for 23 real circuits).
  elif [ "$pan" -gt 0 ] && [ "$pansmd" -eq 0 ] && [[ "$src" =~ ^gerber ]]; then v=THT
  elif [ "$pan" -gt 0 ] && [ "$pansmd" -eq 0 ] && [[ "$src" =~ ^(kicad|eagle|ibom) ]]; then v=THT; src="$src [panel hardware only: $pan through-hole parts, no SMD]"
  elif [ "$pan" -gt 0 ] && [[ "$src" =~ ^(kicad|eagle|ibom) ]]; then v=""; conf=Weak; src="$src [panel hardware only, $pansmd of $pan SMD]"
  else v=""; conf=Deferred; fi
  # unclassified packages block the call only when they could change it: "both" (SMD with a
  # THT IC or 6+ THT passives) survives any extra part, and so does "SMD" while even
  # counting every unknown as a THT passive stays within the 5 limit (the unknown cannot
  # be a DIP/SIP, which E_IC would have matched by name). Otherwise blank, Weak.
  unk=$(tr -s ' ' <<<"$unk" | sed 's/^ //; s/ $//')   # names from every footprint path (no unquoted echo: names may hold *)
  if [ -n "$unk" ]; then
    src="$src [unclassified: $unk]"
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
  failnote="$failnote$stubnote$stencilnote$backupnote$autonote"
  [ -n "$faces" ] && failnote="$failnote; faceplate PCB not counted (no circuit parts): $faces"   # v27
  pnote=""; [ "$PANEL_COUNT" = 1 ] && [[ "$src" =~ ^(kicad|easyeda|eagle|ibom) ]] && pnote=" panel=$pcnt"

  printf '%s\t%s\t%s\t%s (files=%s: %s): smd=%s tht_passive=%s tht_to=%s tht_ic=%s (panel excluded) smd_ic=%s%s%s\t%s\t%s\n' \
    "$r" "$scope" "$v" "$src" "$nused" "$used" "$smd" "$tht" "$tq" "$thtic" "$ic" "$pnote" "$failnote" "$conf" "$DETECTOR_VERSION"
done
