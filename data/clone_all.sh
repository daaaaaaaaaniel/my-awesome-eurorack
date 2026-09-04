#!/bin/bash
cd /tmp/claude-0/-home-user-my-awesome-eurorack/cf915991-761e-5ecd-a5dd-f8d87f9cd3f6/scratchpad
mkdir -p clones trees
: > clone.log
tail -n +2 /home/user/my-awesome-eurorack/data/inventory.tsv | cut -f2 | while read -r r; do
  key=$(echo "$r" | tr '/' '__')
  d="clones/$key"
  if [ -s "trees/$key.txt" ]; then echo "SKIP $r" >> clone.log; continue; fi
  rm -rf "$d"
  if git clone -q --filter=blob:none --depth 1 --no-checkout "https://github.com/$r" "$d" 2>/dev/null; then
    git -C "$d" ls-tree -r HEAD --name-only > "trees/$key.txt" 2>/dev/null
    n=$(wc -l < "trees/$key.txt")
    echo "OK $r $n" >> clone.log
    rm -rf "$d"          # tree is saved; drop the clone to conserve disk
  else
    echo "FAIL $r" >> clone.log
  fi
done
echo "DONE" >> clone.log
