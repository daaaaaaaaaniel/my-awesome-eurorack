#!/bin/bash
# Triage every repo by scanning its saved tree for hardware-design evidence.
INV=/home/user/my-awesome-eurorack/data/inventory.tsv
cd /tmp/claude-0/-home-user-my-awesome-eurorack/cf915991-761e-5ecd-a5dd-f8d87f9cd3f6/scratchpad

# EDA / layout source formats
RX_EDA='\.(kicad_pcb|kicad_sch|kicad_pro|kicad_mod|pro|sch|brd|schdoc|pcbdoc|prjpcb|fzz|fz|diy|pcb|dip|dsn|net|lay6?)$'
# fabrication output
RX_FAB='\.(gbr|ger|gtl|gbl|gts|gbs|gto|gbo|gml|gko|drl|xln|gbrjob)$|gerber'
# parts list
RX_BOM='(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv|html|xlsx|xls|ods)$|(^|/)bom(/|$)|bill.?of.?materials'
# schematic as document
RX_SPDF='(schem|sch)[^/]*\.pdf$'
# hand-wiring layouts
RX_STRIP='stripboard|veroboard|protoboard|perfboard|\.diy$'

printf 'repo\tverdict\teda_kinds\tfab\tbom\tsch_pdf\tstrip\thw_total\tmodule_dirs\tzip\tdocs\n'
tail -n +2 "$INV" | cut -f2 | while read -r r; do
  key=$(echo "$r" | tr '/' '_'); f="trees/$key.txt"
  [ -s "$f" ] || { printf '%s\tNO_TREE\t\t0\t0\t0\t0\t0\t0\t0\t0\n' "$r"; continue; }

  eda=$(grep -icE "$RX_EDA" "$f"); fab=$(grep -icE "$RX_FAB" "$f")
  bom=$(grep -icE "$RX_BOM" "$f"); spdf=$(grep -icE "$RX_SPDF" "$f")
  strip=$(grep -icE "$RX_STRIP" "$f")
  hw=$((eda+fab+bom+spdf+strip))

  kinds=""
  grep -qiE '\.(kicad_pcb|kicad_sch|kicad_pro|kicad_mod)$' "$f" && kinds="${kinds}kicad,"
  grep -qiE '\.brd$' "$f" && kinds="${kinds}eagle,"
  grep -qiE '\.(schdoc|pcbdoc|prjpcb)$' "$f" && kinds="${kinds}altium,"
  grep -qiE '\.(fzz|fz)$' "$f" && kinds="${kinds}fritzing,"
  grep -qiE '\.dip$' "$f" && kinds="${kinds}diptrace,"
  grep -qiE '\.pcb$' "$f" && kinds="${kinds}geda,"
  grep -qiE '\.diy$' "$f" && kinds="${kinds}diylc,"
  grep -qiE 'easyeda' "$f" && kinds="${kinds}easyeda,"
  kinds=${kinds%,}

  # weaker, ambiguous carriers: zipped hardware, document-only schematics/layouts/panels
  zipn=$(grep -icE '\.zip$' "$f")
  docn=$(grep -icE '(schem|layout|panel|pcb|bom|stripboard|veroboard|wiring|circuit|bill.?of.?material)[^ ]*\.(pdf|svg|png|jpg|jpeg|dxf|ai|json)$' "$f")
  # any document-heavy repo: a eurorack repo that is mostly PDFs/SVGs is very
  # likely schematics even when no filename says so (e.g. odeliy/schema-cave)
  pdfn=$(grep -icE '\.(pdf|svg)$' "$f")
  [ "$pdfn" -ge 2 ] && docn=$((docn+pdfn))
  maybe=$((zipn+docn))

  if [ "$hw" -gt 0 ]; then v=HW
  elif [ "$maybe" -gt 0 ]; then v=MAYBE
  else v=NO_HW; fi
  nmod=$(./moduledirs.sh "$r" 2>/dev/null | wc -l)
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$r" "$v" "$kinds" "$fab" "$bom" "$spdf" "$strip" "$hw" "$nmod" "$zipn" "$docn"
done
