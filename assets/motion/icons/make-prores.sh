#!/usr/bin/env bash
# make-prores.sh <slug> <out-dir> [on-dark|on-light] [fps]  — a timeline-ready ProRes 4444 (straight alpha)
# of one icon for hand placement on an app lane (Premiere / Resolve / CapCut: CapCut wants it premultiplied
# afterwards, per the capcut skill). Inside an HTML comp use the .webm directly instead.
#   ./assets/motion/icons/make-prores.sh dinero projects/<job>/hf-graphics/gfx/renders           # on-dark, 29.97
#   ./assets/motion/icons/make-prores.sh dinero projects/<job>/hf-graphics/gfx/renders on-light 24000/1001
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SLUG="$1"; OUT="$2"; VAR="${3:-on-dark}"; FPS="${4:-30000/1001}"
SRC="$HERE/$VAR/$SLUG.webm"; [ -f "$SRC" ] || { echo "no such icon: $SRC" >&2; exit 1; }
mkdir -p "$OUT"
# -c:v libvpx-vp9 on the INPUT: ffmpeg's native vp9 decoder drops the alpha plane (2026-09-14)
ffmpeg -y -v error -c:v libvpx-vp9 -i "$SRC" -vf "fps=$FPS,format=yuva444p10le" \
  -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le "$OUT/icon-$SLUG-$VAR.mov"
echo "-> $OUT/icon-$SLUG-$VAR.mov"
