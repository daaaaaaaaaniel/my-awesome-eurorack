#!/bin/bash
# trial: classify .kicad_sch footprints with components.sh's own KiCad patterns
cd "$HOME/mnt/folder-bus-2/repo"; DATA=data
eval "$(sed -n '/^MECH=/p;/^PANEL=/p;/^SMD_PKG=/p;/^THT_PKG=/p;/^THT_IC=/p;/^THT_TO=/p' data/components.sh | grep -v '^PANEL="\$PANEL' )"; PANEL="$PANEL|$MECH"
export PANEL SMD_PKG THT_PKG THT_IC THT_TO
while IFS=$'\t' read -r id r d; do
  sha=$(awk -F'\t' -v R="$r" '$2==R{print $6}' data/inventory.tsv | tr -d '\r')
  files=$(bash data/modulefiles.sh "$r" "$d" | tail -n +2)
  sch=$(grep '\.kicad_sch$' <<<"$files" | grep -v '_autosave' )
  tmp=$(mktemp)
  while IFS= read -r f; do [ -n "$f" ] && curl -sS -m 40 --fail "https://raw.githubusercontent.com/$r/$sha/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$f")" | python3 data/kicad_sch_parts.py >> "$tmp"; done <<<"$sch"
  if [ ! -s "$tmp" ]; then   # backup zip: newest one with a non-empty schematic
    z=$(grep -E -- '-backups/[^/]*\.zip$' <<<"$files" | sort | tail -1)
    [ -n "$z" ] && curl -sS -m 60 --fail "https://raw.githubusercontent.com/$r/$sha/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$z")" -o "$tmp.zip" && python3 -c "
import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); n=[x for x in z.namelist() if x.endswith('.kicad_sch') and 'autosave' not in x]
sys.stdout.write(''.join(z.read(x).decode('utf-8','replace') for x in n[:1]))" "$tmp.zip" | python3 data/kicad_sch_parts.py > "$tmp"
  fi
  python3 - "$tmp" "$id" "$(grep -c . <<<"$sch")" <<'PY'
import sys, re, os, collections
P, S, T, I, O = (re.compile(os.environ[k]) for k in ("PANEL", "SMD_PKG", "THT_PKG", "THT_IC", "THT_TO"))
P2 = re.compile(r"thonk|alpha9|alpha_?[0-9]|pj-?3[0-9]|cui_sj|sj1-35|jack|pot(entiometer)?[^a-z]|fader", re.I)   # jack/pot library names
T2 = re.compile(r"quarter_watt|C_Rect_|C_Disc_|_L[0-9.]+mm_D[0-9.]+mm", re.I)   # axial / box-film THT names
PANEL_LIB = re.compile(r"Connector|AudioJack|Jack|Switch|SW_|Potentiometer|R_Pot|LED|Mechanical|MountingHole|Conn_|Fiducial|TestPoint|Graphic|Logo", re.I)
rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1]) if l.strip()]
smd = tht = ic = to = pan = unk = none = 0; ul = collections.Counter()
for fp, ref, lib in rows:
    if not fp:
        if PANEL_LIB.search(lib): pan += 1
        else: none += 1; ul["(no footprint) " + lib] += 1
        continue
    if I.search(fp): ic += 1
    elif P.search(fp) or P2.search(fp): pan += 1
    elif O.search(fp): to += 1
    elif S.search(fp): smd += 1; ul['SMD: ' + fp] += 1
    elif T.search(fp) or T2.search(fp): tht += 1
    else: unk += 1; ul[fp] += 1
v = ("both" if smd and (ic or tht > 5) else "SMD" if smd else "THT" if (tht or ic or to) else "")
risk = none + unk
# unassigned/unclassified parts may change the call unless it is already 'both'
if risk and v != "both" and not (v == "SMD" and tht + risk <= 5): v = "(blank)"
print(f"{sys.argv[2]}\tsheets={sys.argv[3]} symbols={len(rows)}\tsmd={smd} tht_passive={tht} tht_ic={ic} tht_to={to} panel={pan} no_fp={none} unclassified={unk}\t-> {v or '(blank)'}\t{'; '.join(f'{k}x{n}' for k, n in ul.most_common(4))[:160]}")
PY
  rm -f "$tmp" "$tmp.zip"
done
