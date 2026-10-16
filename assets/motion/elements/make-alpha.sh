#!/usr/bin/env bash
# make-alpha.sh <el-id> <out-dir> [tint-hex]   — derive an alpha overlay from a white-on-black bed.
#   alpha = luma, colour = white (or the tint), black tail frames trimmed per catalog.json.
#   FORMAT=mov (default, ProRes 4444 straight alpha, 29.97 — Premiere/Resolve/CapCut lanes)
#   FORMAT=webm (VP9 alpha, native rate — for <video> inside an HTML comp)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ID="$1"; OUT="$2"; TINT="${3:-FFFFFF}"; FORMAT="${FORMAT:-mov}"
ROW=$(python3 -c "import json,sys; c=json.load(open('$HERE/catalog.json')); r=[x for x in c if x['id']=='$ID']; sys.exit('unknown id $ID') if not r else print(r[0]['file'], r[0]['black_tail_frames'], r[0]['frames'])")
FILE=$(echo "$ROW" | cut -d' ' -f1); TAIL=$(echo "$ROW" | cut -d' ' -f2); N=$(echo "$ROW" | cut -d' ' -f3)
KEEP=$((N - TAIL))
R=$((16#${TINT:0:2})); G=$((16#${TINT:2:2})); B=$((16#${TINT:4:2}))
MIX="colorchannelmixer=rr=$(python3 -c "print($R/255)"):gg=$(python3 -c "print($G/255)"):bb=$(python3 -c "print($B/255)")"
mkdir -p "$OUT"
if [ "$FORMAT" = "webm" ]; then
  ffmpeg -y -v error -i "$HERE/$FILE" -frames:v "$KEEP" -filter_complex \
    "[0:v]split[c][l];[l]format=gray[a];[c]format=rgba,geq=r=255:g=255:b=255:a=255,$MIX[w];[w][a]alphamerge,format=yuva420p[o]" \
    -map "[o]" -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 24 -auto-alt-ref 0 -deadline good -cpu-used 2 "$OUT/$ID-alpha-$TINT.webm"
  echo "-> $OUT/$ID-alpha-$TINT.webm ($KEEP frames)"
else
  ffmpeg -y -v error -i "$HERE/$FILE" -frames:v "$KEEP" -filter_complex \
    "[0:v]split[c][l];[l]format=gray[a];[c]format=rgba,geq=r=255:g=255:b=255:a=255,$MIX[w];[w][a]alphamerge,format=yuva444p10le[o]" \
    -map "[o]" -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -r 30000/1001 "$OUT/$ID-alpha-$TINT.mov"
  echo "-> $OUT/$ID-alpha-$TINT.mov ($KEEP frames, ProRes 4444 straight alpha)"
fi
