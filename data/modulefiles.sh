#!/bin/bash
# List the files that belong to ONE module of a repo, from its saved tree.
#
#   usage: modulefiles.sh owner/repo [module_dir]
#   output: first line "SCOPE<TAB><resolved dir>", then one path per line.
#
#   module_dir given (not "."): files under module_dir/.
#   "." or omitted: the ROOT module = files NOT under any other detected module dir.
#     If the root holds no design files and exactly one other module dir exists, the
#     module lives in that subfolder (e.g. Fihdi/MiniDrumkit -> MiniDrumkit2) and the
#     scope resolves to it.
#
# This is the single place scoping is decided; components.sh and extract.sh both use it,
# so a collection's modules never pool their files into one verdict.
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TREES="${TREES:-$DATA/trees}"
r=$1; want=${2:-.}
f="$TREES/$(echo "$r" | tr '/' '_').txt"
[ -s "$f" ] || { echo "modulefiles.sh: no tree for $r" >&2; exit 1; }

HW='\.(kicad_pcb|kicad_sch|kicad_pro|brd|sch|schdoc|pcbdoc|fzz|diy|dip|pcb)$|/gerber|\.(gbr|gtl|gbl|drl)$|bom[^/]*\.(csv|xlsx|xls|md|txt)$|schematic[^/]*\.pdf$'
OTHERS=$(TREES="$TREES" bash "$DATA/moduledirs.sh" "$r" | sed -E 's/^ *[0-9]+ //' | grep -vxF '.')
export OTHERS

scope_files() {
  if [ "$1" = "." ]; then   # root module: exclude every other module's subtree
    awk 'BEGIN{n=split(ENVIRON["OTHERS"],o,"\n")}
         {for(i=1;i<=n;i++) if(o[i]!="" && index($0,o[i]"/")==1) next; print}' "$f"
  else                      # literal prefix match: dir names contain & ( ) spaces
    D="$1/" awk 'index($0,ENVIRON["D"])==1' "$f"
  fi
}

files=$(scope_files "$want")
if [ "$want" = "." ] && ! grep -qiE "$HW" <<<"$files" && [ "$(grep -c . <<<"$OTHERS")" -eq 1 ]; then
  want=$OTHERS; files=$(scope_files "$want")
fi
printf 'SCOPE\t%s\n' "$want"
grep -v '^$' <<<"$files"
exit 0
