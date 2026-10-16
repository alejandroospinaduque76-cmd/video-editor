#!/usr/bin/env bash
# splice.sh — cuts + concatenates clips per cuts.json
# usage: splice.sh <job_dir>
# reads:  $VIDEO_EDITOR_WORK/<job-name>/cuts.json  (default /tmp/video-editor/<job-name>/cuts.json)
# writes: projects/<job-name>/outputs/<job-name>.mp4

set -euo pipefail

# Python launcher, probed by RUNNING it: macOS/Linux have `python3`; Windows installs it
# as `python` (and ships a fake `python3` Store stub that only opens the Microsoft Store,
# which `command -v` can't see through).
PY=python3; "$PY" -c '' 2>/dev/null || PY=python
# Windows pipes default python stdio to cp1252, which can't encode the ⚠/→/✓ glyphs the
# pipeline's status lines use; export-transcript.py died mid-splice on a real job
# (2026-08-13). UTF-8 mode fixes stdio AND default open() encoding; no-op on macOS/Linux.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

JOB_DIR="${1:?usage: splice.sh <job_dir>}"
JOB_DIR="$(cd "$JOB_DIR" && pwd)"
JOB_NAME="$(basename "$JOB_DIR")"
# ONE scratch root shared with transcribe.sh and every python helper (2026-09-25): Git Bash maps
# /tmp to %TEMP% while native Windows Python reads "/tmp/..." as C:\tmp\..., so this script and
# polish-boundaries.py used to write different folders on Windows. VIDEO_EDITOR_WORK wins if set,
# else /tmp/video-editor; exported (as a C:/... mixed path on Windows) so the helpers inherit it.
WORK_ROOT="${VIDEO_EDITOR_WORK:-/tmp/video-editor}"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*)
  command -v cygpath >/dev/null 2>&1 && WORK_ROOT="$(cygpath -m "$WORK_ROOT")" ;;
esac
export VIDEO_EDITOR_WORK="$WORK_ROOT"
WORK="$WORK_ROOT/$JOB_NAME"
MEDIA_DIR="$JOB_DIR"
[ -d "$JOB_DIR/raw" ] && MEDIA_DIR="$JOB_DIR/raw"
OUT="$JOB_DIR/outputs"
CUTS="$WORK/cuts.json"
mkdir -p "$WORK" "$OUT"

[ -f "$CUTS" ] || { echo "missing $CUTS" >&2; exit 1; }

# EDL OVERWRITE GUARD. This splice ends by copying the EDL it spliced over transcript/cuts.json. When that file
# changed after the last splice (cut-audit.py --promote, live-edl.py --write, a hand edit) and the /tmp EDL is not
# that file, the copy would silently replace the newer cut with a stale one. The stamp lives in the job folder
# (transcript/cuts.splice.sha1), never in /tmp: polish-boundaries.py deletes cuts.snapped.json.
sha1_of() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 1 "$1" | cut -d' ' -f1
  else "$PY" -c 'import hashlib,sys; print(hashlib.sha1(open(sys.argv[1],"rb").read()).hexdigest())' "$1"; fi
}
JOB_EDL="$JOB_DIR/transcript/cuts.json"; STAMP="$JOB_DIR/transcript/cuts.splice.sha1"
if [ -f "$JOB_EDL" ] && [ -f "$STAMP" ] && [ "$(sha1_of "$JOB_EDL")" != "$(cat "$STAMP")" ] \
   && ! cmp -s "$WORK/cuts.json" "$JOB_EDL"; then
  echo "[splice] ✗ transcript/cuts.json was written after the last splice (cut-audit --promote, live-edl --write or a" >&2
  echo "    hand edit): cp it to $WORK/cuts.json first, or this splice would overwrite it." >&2
  echo "    job EDL: $JOB_EDL" >&2
  echo "    /tmp EDL: $WORK/cuts.json" >&2
  exit 2
fi

# BOUNDARY REFINE — measured onset/offset dial-in (refine-cuts.py). WhisperX word
# START timestamps run ~50-100 ms late vs the real acoustic attack, so cuts authored
# at word.start-minus-pad still land INSIDE the word and clip its onset (a real job
# shipped a sentence-opening word with its first 48 ms missing); word ENDS run
# early the same way and clip decays. The refiner measures each chosen word's
# acoustic edge on the raw audio (5 ms RMS envelope) and moves the cut just outside
# it — in = onset−40 ms, out = offset+50 ms — clamped inside the local gap so it can
# never cross an adjacent word. Cut CHOICE stays Claude's; this only dials the
# boundary of the word already chosen (never snapping a cut to the nearest silence —
# the "don't auto-snap to silence" gotcha still stands). REFINE=0 skips the pass;
# "no_refine": true on a segment skips just that segment.
WORDS_SRC="$JOB_DIR/transcript/words.json"; [ -f "$WORDS_SRC" ] || WORDS_SRC="$WORK/words.json"
if [ "${REFINE:-1}" != "0" ] && [ -f "$WORDS_SRC" ]; then
  if "$PY" "$(dirname "$0")/refine-cuts.py" "$MEDIA_DIR" "$WORDS_SRC" "$CUTS" "$WORK/cuts.refined.json"; then
    CUTS="$WORK/cuts.refined.json"
  else
    echo "[splice] ⚠ refine-cuts failed — splicing authored cuts.json unrefined" >&2
  fi
fi

# cuts.json schema:
# { "segments": [ { "clip": "clip-01.mov", "start": 1.2, "end": 4.8 }, ... ] }

# SINGLE-PASS CLEAN SPLICE — cut + concat happen in ONE ffmpeg filtergraph, and the audio
# polish (static gain → hard limiter) is applied exactly ONCE to the assembled track, then
# encoded to AAC exactly ONCE. This is the "cut from raw, master once at the end" order:
#   • Audio rides through the cut LOSSLESS (PCM in the filtergraph) — NEVER encoded per-segment.
#     The old approach encoded each segment to AAC, copy-concatenated those AAC chunks (each join
#     splices in ~1024+ samples of AAC encoder priming = a tiny CLICK at every cut), then encoded
#     AAC a 2nd time. Two lossy generations + a click per boundary on pristine PCM source audio.
#     Processing per-segment before assembly is the bug; processing once after assembly is the fix.
#   • A/V stay LOCKED by construction: video and audio are trimmed from the SAME in/out points in
#     the same graph and concatenated together — no independent rebuild that could drift.
#   • trim/setpts rebases the first frame to pts 0 (no empty edit / QuickTime black-flash), verified.
#
# Audio chain — STATIC gain + hard limiter (the classic Premiere Amplify + Hard Limiter move). NOT loudnorm: single-pass
#   loudnorm runs DYNAMIC (rides gain over time) and PUMPS. This is static + transparent: constant
#   +AMPLIFY_DB gain, peaks brickwalled at −6 dBFS, zero time-varying leveling. Raw record level is
#   ~−30 dB mean, which is what the gain is calibrated against. `level=disabled` is REQUIRED —
#   alimiter's auto-level defaults ON and re-normalizes loud (clips to +TP / crushes LRA);
#   limit=0.501 = −6 dBFS. AMPLIFY_DB is the only loudness knob and, unset, it is MEASURED:
#   workflows/voice-gain.py puts the raw's kept speech at −17 LUFS integrated pre-limiter (locked
#   2026-09-03 on a real job where +15 dB measured right: the house sound runs the limiter hard on
#   purpose, which reverses the 2026-06-28 "+15 too hard" call). AMPLIFY_DB overrides it, which is a DEVIATION
#   from the locked measurement: stated in the report and written into RUN.md, never a way round a
#   failed measurement (LANES.md § step 3 owns the rule).
"$PY" - "$MEDIA_DIR" "$CUTS" "$OUT/${JOB_NAME}.mp4" "$JOB_DIR" "$(cd "$(dirname "$0")/../../../.." && pwd)" <<'PY'
import json, os, sys, subprocess, platform
media_dir, cuts_path, out_path, job_dir, repo = sys.argv[1:]
amp = os.environ.get("AMPLIFY_DB")
if not amp and os.environ.get("RENDER", "1") == "0":
    amp = "0"   # EDL-only mode never renders, so the gain is never applied here; step 3 measures its own
if not amp:
    # the measured gain (kept speech -> -17 LUFS pre-limiter); a failure here is loud, never a silent +10.
    # Resolved from the REPO root, not the cuts path: cuts live in /tmp/video-editor/<job>/ (2026-09-03 fix).
    # Measured on the EDL this splice renders (--edl: the refined one when refine ran), never on a
    # transcript/cuts.json from an earlier splice, or missing on a first one (a fresh clipper clip).
    vg = os.path.join(repo, "workflows", "voice-gain.py")
    r = subprocess.run(["uv", "run", vg, job_dir, "--json", "--edl", cuts_path], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("voice-gain.py failed - FIX it; AMPLIFY_DB overrides the locked measurement "
                         "and must be announced:\n" + (r.stderr or r.stdout))
    amp = str(json.loads(r.stdout)["gain_db"])
    print(f"[splice] AMPLIFY_DB measured: {amp} dB (voice-gain.py)")
with open(cuts_path) as f:
    segs = json.load(f)["segments"]
if not segs:
    raise SystemExit("cuts.json has no segments")

# One -i per unique clip; segments reference the right input index.
inputs, idx = [], {}
def resolve_clip(clip):
    """cuts.json clip name -> file. Exact path first, then the same STEM in raw/: from
    2026-09-25 workflows/normalize-source.py moves originals into raw/_source/ and writes the
    normalized copy as <stem>.mov, so an EDL authored against IMG_1.MOV must find IMG_1.mov
    (case-sensitive filesystems: Linux, some Windows setups). Temp files and dotfiles never match."""
    p = clip if os.path.isabs(clip) else os.path.join(media_dir, clip)
    if os.path.exists(p):
        return p
    stem = os.path.splitext(os.path.basename(clip))[0].lower()
    try:
        names = sorted(os.listdir(media_dir))
    except OSError:
        names = []
    hits = [f for f in names
            if not f.startswith(".") and ".normalizing." not in f
            and os.path.isfile(os.path.join(media_dir, f))
            and os.path.splitext(f)[0].lower() == stem]
    if len(hits) == 1:
        print(f"[splice] {clip} not in raw/; using same-stem {hits[0]}", file=sys.stderr)
        return os.path.join(media_dir, hits[0])
    raise SystemExit(f"clip not found: {p}" + (f" (ambiguous same-stem files: {hits})" if hits else ""))

def input_index(clip):
    p = resolve_clip(clip)
    if p not in idx:
        idx[p] = len(inputs); inputs.append(p)
    return idx[p]

# FRAME-GRID SNAP — the silence-gap fix. Video trim keeps whole frames while atrim cuts
# sample-exact, so un-snapped fractional cut times give every segment a video duration up
# to ±1 frame different from its audio duration. concat (v=1:a=1) then pads the shorter
# audio with DIGITAL ZEROS at each joint — measured +120 ms of inserted silence across one
# real 16-segment job: audible room-tone dropouts, extra click edges, and a progressive
# timeline stretch that desyncs the transcript/captions (the long-standing "render cut
# drift"). Snapping every boundary to the video frame grid makes video and audio durations
# IDENTICAL per segment: concat pads nothing, joints are pure (faded) butt-joins, and the
# output timeline equals the snapped cuts.json exactly.
STD_RATES = ((24000, 1001), (24, 1), (25, 1), (30000, 1001), (30, 1), (48000, 1001), (48, 1), (50, 1), (60000, 1001),
             (60, 1), (100, 1), (120000, 1001), (120, 1))


def video_fps(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=r_frame_rate,avg_frame_rate", "-of", "json", path],
                         capture_output=True, text=True).stdout
    # json, not csv: iPhone .MOV footage carries stream side data, which the csv writer emits as extra
    # elements/rows ("30000/1001," with a trailing comma crashed int() once, 2026-08-13, real job)
    st = json.loads(out or "{}").get("streams", [{}])[0]
    num, den = (int(x) for x in st["r_frame_rate"].split("/"))
    try:
        an, ad = (int(x) for x in st.get("avg_frame_rate", "0/0").split("/"))
        avg = an / ad
    except (ValueError, ZeroDivisionError):
        avg = 0.0
    # The grid below snaps every boundary AND conforms the stream to it (fps=), so a nonsense r_frame_rate would
    # multiply frames: a heavily jittered test file read r 30000/1 and a 0.3 s segment rendered 9000 frames
    # (2026-09-27). Only a nominal rate that is BOTH off every standard rate and not backed by the average (off by more
    # than 2%) gives way to the standard rate nearest the average: a QuickTime screen recording at r 60/1 whose static
    # stretches write fewer frames (avg 30) keeps its 60 grid, a 15 fps capture keeps 15, and a phone take's r
    # 30000/1001 against avg 29.977 stays as it is.
    std = any(abs(num / den - a / b) < 1e-3 for a, b in STD_RATES)
    if avg > 0 and not std and abs(num / den - avg) / avg > 0.02:
        sn, sd = min(STD_RATES, key=lambda r: abs(r[0] / r[1] - avg))
        print(f"[splice] ⚠ {os.path.basename(path)}: r_frame_rate {num}/{den} is not backed by its average "
              f"{avg:.3f} fps: the grid is {sn}/{sd}", file=sys.stderr)
        return sn, sd
    return num, den

# MULTI-CLIP NORMALIZATION (2026-09-25). concat needs every video segment at the same size and
# SAR, and a segment needs an audio stream to trim: a job mixing an iPhone 4K60 take, a 1080p30
# clip and a QuickTime screen recording (no audio track at all) failed inside the filtergraph.
# Each input is probed once for its DISPLAY geometry (rotation and SAR applied, what a player
# shows) and whether it has audio. Only when the inputs used by the EDL actually differ does the
# graph normalize video to the first dialogue clip (the first segment's clip that has audio):
# fps to its rate BEFORE the trim (so every segment is a whole number of target frames), then
# fit + pad to its display size with square pixels, yuv420p. Inputs without audio get exact-
# length digital silence. A single-clip job, or clips that already match, build the same graph
# as before, filter for filter.
def probe_input(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=index,codec_type,width,height,sample_aspect_ratio,color_space"
                        ":stream_side_data=rotation:stream_tags=rotate", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        streams = json.loads(r.stdout or "{}").get("streams", [])
    except ValueError:
        streams = []
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    sar_s = str(v.get("sample_aspect_ratio") or "1:1")
    try:
        sn, sd = (int(x) for x in sar_s.split(":"))
        sar = sn / sd if sn > 0 and sd > 0 else 1.0
    except ValueError:
        sar = 1.0
    rot = 0
    for sd_ in v.get("side_data_list", []) or []:
        if "rotation" in sd_:
            rot = int(float(sd_["rotation"]))
    if not rot and (v.get("tags") or {}).get("rotate"):
        rot = int(float(v["tags"]["rotate"]))
    dw = int(round(w * sar / 2)) * 2 if abs(sar - 1.0) > 1e-3 else w
    dh = h
    if abs(rot) % 180 == 90:
        dw, dh = dh, dw
    return {"disp": (dw, dh), "sar": sar, "fps": video_fps(path), "audio": has_audio,
            "csp": str(v.get("color_space") or "unknown")}

# BT.709 ON THE FRAMES (2026-09-29). Homebrew ffmpeg 9.0.1 ignores the -color_primaries/-color_trc
# flags below when the source frames carry no colour tags (a screen recording, a synthetic clip),
# AND, asked for -colorspace bt709, its auto-scaler reads the untagged matrix as BT.601 and converts
# it: the cut shipped primaries/transfer "unknown" plus a silent colour shift (mean Y -0.9, U -0.3,
# V -0.6 code values, measured). setparams labels an untagged (or already BT.709) input as BT.709:
# no conversion, all three tags written. A clip TAGGED with another matrix (BT.601 from some
# Android phones) is left alone: ffmpeg's matrix conversion is right for it. BT.709-tagged footage
# (iPhone SDR, normalize-source.py output) decodes to the same frames as before.
def tag709(k):
    return (",setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"
            if info[k]["csp"] in ("unknown", "bt709") else "")

parts, vlabels = [], []
# Joint treatment: J-CUT CROSSFADES, not fades-to-zero. A butt-splice clicks whenever a
# joint misses a zero crossing (measured 1-sample jumps up to ~80x local signal), but
# fading each edge down to silence trades the click for a ~20 ms ROOM-TONE HOLE at every
# joint — measured 8-13 dB ambience dips, still audible on headphones. The editorial fix:
# each segment's AUDIO runs XF seconds PAST its video cut (real continuing room tone from
# the raw) and equal-power crossfades into the next segment's head. Ambience never dips,
# a step discontinuity is impossible, and the chain arithmetic keeps timing exact:
# sum((dur_i + XF)) - (n-1)*XF == sum(dur_i) == video duration. The rising head gain also
# softens mouth/lip transients that sit a few ms after cut-ins (word starts run late vs
# acoustic onsets). This is part of the CUT (a DAW's auto-crossfade), NOT per-segment
# mastering — the gain->limiter->encode chain still runs exactly once on the whole track.
XF = 0.015          # default crossfade at each joint (min word padding ~31 ms, speech untouched)
EDGE = 0.005        # tiny fade from/to silence at the very start and end of the file
# Per-joint override: a segment may carry "xfade": <seconds> in cuts.json — the crossfade
# INTO that segment uses it instead of XF. Use when a cut-in clips an already-in-progress
# acoustic onset (word attacks often start tens of ms before the word timestamp): a longer
# ramp (e.g. 0.06) rebuilds a natural attack without moving the timeline.
def xf_into(i):
    return float(segs[i].get("xfade", XF)) if 0 < i < len(segs) else 0.0
max_shift = 0.0
n = len(segs)
seg_k = [input_index(s["clip"]) for s in segs]
info = {k: probe_input(inputs[k]) for k in sorted(set(seg_k))}
ref_k = next((k for k in seg_k if info[k]["audio"]), seg_k[0])   # first DIALOGUE clip
ref = info[ref_k]
TW, TH = ref["disp"]
TFN, TFD = ref["fps"]
from fractions import Fraction
normalize = len({(i_["disp"], Fraction(*i_["fps"]), abs(i_["sar"] - 1.0) > 1e-3)
                 for i_ in info.values()}) > 1
if normalize:
    print(f"[splice] mixed inputs — normalizing video to {TW}x{TH} @ {TFN}/{TFD} fps "
          f"(first dialogue clip {os.path.basename(inputs[ref_k])}): "
          + ", ".join(f"{os.path.basename(inputs[k])} {i_['disp'][0]}x{i_['disp'][1]}"
                      f"@{i_['fps'][0]}/{i_['fps'][1]}" + ("" if i_["audio"] else " (no audio)")
                      for k, i_ in info.items()), file=sys.stderr)
for k, i_ in info.items():
    if not i_["audio"]:
        print(f"[splice] {os.path.basename(inputs[k])} has no audio track — its segments get "
              "exact-length silence", file=sys.stderr)

def vchain(k):
    """per-segment video filters AFTER trim/setpts; empty unless normalizing"""
    if not normalize:
        return ""
    sq = ""
    if abs(info[k]["sar"] - 1.0) > 1e-3:   # anamorphic: square the pixels before fitting
        sq = ",scale='trunc(iw*sar/2)*2':ih,setsar=1"
    return (f"{sq},scale={TW}:{TH}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            f"pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p")

for i, seg in enumerate(segs):
    a, b = float(seg["start"]), float(seg["end"])
    if b <= a:
        raise SystemExit(f"segment {i} has end <= start: {seg}")
    k = seg_k[i]
    # normalizing: every boundary snaps to the TARGET grid (fps runs before trim, so the
    # segment is exactly (b-a)*fps target frames and audio stays equal to video)
    fn, fd = (TFN, TFD) if normalize else video_fps(inputs[k])
    sa = round(a * fn / fd) * fd / fn
    sb = round(b * fn / fd) * fd / fn
    if sb <= sa:
        sb = sa + fd / fn
    max_shift = max(max_shift, abs(sa - a), abs(sb - b))
    seg["start"], seg["end"] = a, b = sa, sb
    # CONFORM to the nominal grid BEFORE the trim: an iPhone .MOV is variable frame rate (avg 29.988 against a
    # 30000/1001 r_frame_rate), so a time trim straight off the stream kept one frame too many or too few at some
    # joints and the flat cut's V1 cuts landed a frame off the EDL (2 of 6 on a real job, 2026-09-27; the flash scan
    # of the chat-only composite caught it). fps= puts every frame on the grid the boundaries were snapped to
    # (the normalize target's rate on a mixed job, which is the same fn/fd).
    parts.append(f"[{k}:v]fps={fn}/{fd},trim={a}:{b},setpts=PTS-STARTPTS{vchain(k)}{tag709(k)}[v{i}]")
    ext = xf_into(i + 1) if i < n - 1 else 0.0   # tail extension feeds the next joint's crossfade
    edge = ""
    if i == 0:
        edge += f",afade=t=in:st=0:d={EDGE}"
    if i == n - 1:
        edge += f",afade=t=out:st={max(0.0, (b - a) - EDGE):.6f}:d={EDGE}"
    if info[k]["audio"]:
        parts.append(f"[{k}:a]atrim={a}:{b + ext},asetpts=PTS-STARTPTS,aresample=48000:ochl=stereo{edge}[a{i}]")
    else:
        # no audio track: digital silence, sample-exact to the segment (+ its crossfade tail)
        ns = int(round((b + ext - a) * 48000))
        parts.append(f"anullsrc=r=48000:cl=stereo,atrim=end_sample={ns},asetpts=PTS-STARTPTS{edge}[a{i}]")
    vlabels.append(f"[v{i}]")
parts.append("".join(vlabels) + f"concat=n={n}:v=1:a=0[vc]")
cur = "a0"
for i in range(1, n):
    nxt = "ac" if i == n - 1 else f"ax{i}"
    parts.append(f"[{cur}][a{i}]acrossfade=d={xf_into(i)}:c1=qsin:c2=qsin[{nxt}]")
    cur = nxt
if n == 1:
    parts.append("[a0]anull[ac]")
# latency=1: alimiter's 5 ms lookahead otherwise delays the audio 239 samples relative
# to video (measured) — compensation keeps A/V aligned by construction.
parts.append(f"[ac]volume={amp}dB,"
             "alimiter=level_in=1:level_out=1:limit=0.501:attack=5:release=50:level=disabled:latency=1[ao]")
fc = ";".join(parts)

# Video encoder, cross-platform: Apple's hardware encoder (videotoolbox) on macOS for speed;
# libx264 everywhere else (Windows/Linux) — always present in any ffmpeg build, no GPU needed.
# CRF 18 is visually ≈ the videotoolbox target for a talking-head source.
# Bitrate SCALES with the picture (2026-09-25): a flat 8 Mb/s was right for 1080p30 and starved
# a 4K60 iPhone take (~0.016 bits/pixel/frame, blocky in motion), and this file is re-encoded
# again downstream, so its losses compound. Target 0.12 bits per pixel per frame of the OUTPUT
# (1080p30 = 8 Mb/s floor, 1080x1920@60 = 15, 4K60 = 60). The explicit BT.709 tags stop players
# and the next encode from guessing the matrix (untagged HD is read as 601 by some): sources are
# SDR here (workflows/normalize-source.py tone-maps HDR first).
def videotoolbox_ok():
    """Apple's hardware H.264 encoder can refuse to open: a Mac VM with no media engine answers "Cannot create
    compression session: -12908" (the Intel CI Mac, 2026-09-30, where every render of the edit failed on it), and a
    busy encoder can too. A 0.2 s test encode decides; libx264 takes over when it fails. VE_NO_VIDEOTOOLBOX=1 forces
    the software encoder (tests, or a Mac where the hardware encoder misbehaves)."""
    if platform.system() != "Darwin" or os.environ.get("VE_NO_VIDEOTOOLBOX") == "1":
        return False
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:r=30:d=0.2",
                        "-c:v", "h264_videotoolbox", "-b:v", "2M", "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


kbps = max(8000, int(round(0.12 * TW * TH * TFN / TFD / 1000.0)))
colour = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
VT = videotoolbox_ok()
if VT:
    venc = ["-c:v", "h264_videotoolbox", "-b:v", f"{kbps}k", *colour]
else:
    venc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", *colour]
print(f"[splice] video: {TW}x{TH} @ {TFN / TFD:.3f} fps · "
      + (f"videotoolbox {kbps / 1000:.0f} Mb/s" if VT else "libx264 CRF 18"
         + (" (the Mac's hardware encoder did not open)" if platform.system() == "Darwin" else ""))
      + " · BT.709", file=sys.stderr)

# NO-DUPLICATE-FRAMES GUARD. Two boundaries of one joint are measured independently
# (refine-cuts.py) and can cross, which lays the same source frames down twice — a
# 1-15 frame stutter that is invisible in every per-segment check (each segment is
# individually fine; only the PAIR is wrong) and that propagates into the flat render
# AND every EDL replay downstream. refine-cuts.py resolves joints pairwise now, but the
# EDL can also be hand-authored or come in with REFINE=0, so the invariant is asserted
# HERE, on the exact times that ship, after the snap. Fail loud: a stutter that reaches
# a timeline costs a rebuild, and on a hand-edited timeline there is no clean rebuild.
bad = []
for i in range(len(segs) - 1):
    x, y = segs[i], segs[i + 1]
    if os.path.basename(x["clip"]) != os.path.basename(y["clip"]):
        continue
    if x["start"] < y["start"] < x["end"]:
        xn, xd = (TFN, TFD) if normalize else video_fps(inputs[input_index(x["clip"])])
        bad.append((i, x["end"], y["start"], xn / xd))
if bad:
    lines = "\n".join(
        f"    seg{i} ends {e:.3f} but seg{i + 1} starts {s:.3f} "
        f"— {(e - s) * 1000:.0f} ms ({(e - s) * r:.1f} frames) played twice"
        for i, e, s, r in bad)
    raise SystemExit(
        f"[splice] ABORT — {len(bad)} joint(s) reuse the same source frames:\n{lines}\n"
        "    Overlapping segments duplicate footage at the cut and read as a stutter.\n"
        "    A continuous split (nothing removed between two segments) must share ONE\n"
        "    boundary time, not a padded end AND a padded start. Fix cuts.json, or let\n"
        "    refine-cuts.py resolve it (this ran with REFINE=0, or BOTH sides of the\n"
        "    joint are no_refine-pinned — joint resolution never moves a pinned boundary).")

# persist the SNAPPED cut times — the canonical EDL and the caption transcript must
# describe the timeline that actually shipped, not the pre-snap request.
snapped = os.path.join(os.path.dirname(cuts_path), "cuts.snapped.json")
with open(snapped, "w") as f:
    json.dump({"segments": segs}, f, indent=1)
print(f"[splice] frame-grid snap: max boundary shift {max_shift*1000:.1f} ms -> {snapped}",
      file=sys.stderr)

# RENDER=0 — EDL-only mode (every app finish: Premiere, Resolve, CapCut — and the FIRST
# splice on any lane, chat-only included): the timeline replay + canonical transcript need
# only the refined/snapped EDL, so skip the flat render entirely.
if os.environ.get("RENDER", "1") == "0":
    print("[splice] RENDER=0 — EDL-only: skipping the flat render", file=sys.stderr)
    sys.exit(0)

cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
for p in inputs:
    cmd += ["-i", p]
cmd += ["-filter_complex", fc, "-map", "[vc]", "-map", "[ao]",
        *venc,
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        "-video_track_timescale", "90000", "-movflags", "+faststart",
        out_path]
sys.exit(subprocess.run(cmd).returncode)
PY

if [ "${RENDER:-1}" != "0" ]; then
  echo "[splice] wrote $OUT/${JOB_NAME}.mp4" >&2
  ffprobe -hide_banner -loglevel error -show_entries format=duration -of default=nw=1:nk=1 "$OUT/${JOB_NAME}.mp4"
fi

# Persist the EDL durably alongside the canonical raw-timeline transcript.
# cuts.json otherwise lives only in /tmp (macOS clears it). The `premiere-pro`
# app-finish replay rebuilds the cut as separate timeline clips FROM this EDL, so it must
# survive past this session — same raw-timeline domain as transcript/words.json.
mkdir -p "$JOB_DIR/transcript"
# the frame-snapped EDL is the canonical one — it describes the timeline that shipped
EDL="$WORK/cuts.snapped.json"; [ -f "$EDL" ] || EDL="$CUTS"
cp "$EDL" "$JOB_DIR/transcript/cuts.json" \
  && echo "[splice] persisted EDL (frame-snapped) → $JOB_DIR/transcript/cuts.json" >&2
sha1_of "$JOB_DIR/transcript/cuts.json" > "$STAMP"     # the EDL this splice wrote: the guard above reads it

# Derive the cut-aligned caption transcript from the SAME large-v3 words — no re-transcription.
# The locked caption presets + graphics-plan consume this instead of running their own whisper.
WORDS="$JOB_DIR/transcript/words.json"; [ -f "$WORDS" ] || WORDS="$WORK/words.json"
if [ -f "$WORDS" ]; then
  "$PY" "$(dirname "$0")/export-transcript.py" "$WORDS" "$EDL" "$OUT/${JOB_NAME}.transcript.json" >&2 \
    && echo "[splice] derived caption transcript → $OUT/${JOB_NAME}.transcript.json" >&2
fi

# Audio self-check: joint declick verification + limiter-pressure report (advisory).
# Needs the rendered file — skipped in EDL-only mode.
if [ "${RENDER:-1}" != "0" ]; then
  "$PY" "$(dirname "$0")/audio-qa.py" "$JOB_DIR" >&2 || true
fi
