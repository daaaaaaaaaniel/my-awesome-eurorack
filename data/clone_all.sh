#!/bin/bash
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # this script's dir = repo/data
INV="${INV:-$DATA/inventory.tsv}"
TREES="${TREES:-$DATA/trees}"
WORK="${WORK:-$(mktemp -d)}"   # throwaway clones + log
echo "work dir: $WORK" >&2
cd "$WORK"
mkdir -p clones "$TREES"
: > clone.log
tail -n +2 "$INV" | cut -f2 | while read -r r; do
  key=$(echo "$r" | tr '/' '__')
  d="clones/$key"
  if [ -s "$TREES/$key.txt" ]; then echo "SKIP $r" >> clone.log; continue; fi
  rm -rf "$d"
  if git clone -q --filter=blob:none --depth 1 --no-checkout "https://github.com/$r" "$d" 2>/dev/null; then
    git -C "$d" -c core.quotePath=false ls-tree -r HEAD --name-only > "$TREES/$key.txt" 2>/dev/null
    n=$(wc -l < "$TREES/$key.txt")
    echo "OK $r $n" >> clone.log
    rm -rf "$d"          # tree is saved; drop the clone to conserve disk
  else
    echo "FAIL $r" >> clone.log
  fi
done
echo "DONE" >> clone.log
