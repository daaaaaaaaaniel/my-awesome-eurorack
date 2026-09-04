#!/bin/bash
# Module directory = path prefix after skipping generic CONTAINER dirs at the top
# and stopping before the first PART-like dir (Gerber, Panel, BOM, Electronics...).
# Handles nested taxonomies (CATs) and single-module repos with internal folders.
key=$(echo "$1" | tr '/' '_'); f="trees/$key.txt"
[ -s "$f" ] || { echo "NO_TREE"; exit 1; }
grep -iE '\.(kicad_pcb|kicad_sch|kicad_pro|brd|sch|schdoc|pcbdoc|fzz)$|/gerber|\.(gbr|gtl|gbl|drl)$|bom[^/]*\.(csv|xlsx|xls|md|txt)$|schematic[^/]*\.pdf$' "$f" \
| awk -F/ '
function norm(s){ s=tolower(s); gsub(/^[0-9]+[ _.-]*/,"",s); gsub(/[ _-]+/," ",s); gsub(/^ +| +$/,"",s); return s }
BEGIN{
  split("modules|module|eurorack|projects|project|hardware|hw|designs|design|synth|synths|boards", C, "|")
  for(i in C) cont[C[i]]=1
  split("gerber|gerbers|gerber files|gerberfiles|panel|panels|front panel|frontpanel|back panel|bom|boms|bom files|main board|mainboard|board|boards|doc|docs|documentation|image|images|img|photo|photos|pictures|firmware|code|software|sch|schematic|schematics|pcb|pcbs|electronics|main|front|control|cad|kicad|eagle|easyeda|production|production files|fab|output|outputs|plots|3d|stl|bin|build|assets|lib|libs|symbols|footprints|datasheet|datasheets|test|tests|src|panels and boards|tayda|manual|guide|guides", P, "|")
  for(i in P) part[P[i]]=1
}
{
  if (NF==1) { print "."; next }
  i=1
  while (i<NF && cont[norm($i)]) i++      # skip generic top wrappers
  k=i-1
  j=i
  while (j<NF && !part[norm($j)]) { k=j; j++ }
  if (k<i) { print "."; next }            # first real segment already part-like
  d=""
  for(m=1;m<=k;m++) d = d (m>1?"/":"") $m
  print d
}' | sort | uniq -c | sort -rn
