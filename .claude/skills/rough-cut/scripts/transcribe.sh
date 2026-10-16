#!/usr/bin/env bash
# transcribe.sh — runs WhisperX (large-v3 + wav2vec2 forced alignment) on every clip in a job folder
# usage: transcribe.sh <job_dir> [--diarize] [--force] [--lang <code>] [--chunk-size N] [--vad-onset X --vad-offset Y]
#        transcribe.sh --file <audio|video> --out <words.json> [--diarize] [--lang <code>] [--chunk-size N] [--vad-...]
#        transcribe.sh --prefetch [--lang <code>]
# standalone (--file/--out): one file in (a pickup re-record, a spliced audio), the same words.json shape out at
#           --out. It never reads or writes a job's transcript/: no canonical, no reuse, always transcribes.
# language: auto-detected per clip by default (WhisperX large-v3). Force one with
#           --lang es|en|pt|… or WHISPERX_LANG=es. A forced English default used to
#           silently TRANSLATE non-English speech with fictional timestamps (2026-09-21).
#           v1.3: with neither given, the creator's style profile `idioma` (workflows/profile.py)
#           is used when it is not "auto"; no profile → auto-detect, exactly as before.
# --prefetch (v1.3): build the whisperx venv and download large-v3 + the wav2vec2 aligner for
#           the profile language (es when the profile says auto / no profile), then exit. No job
#           dir. Idempotent: says "already present" and exits fast when everything is cached.
#           Onboarding (`empezar`) starts it in the background during the interview; the full
#           output goes to $VIDEO_EDITOR_WORK/_prefetch/prefetch.log.
# output: <job_dir>/transcript/words.json  (durable canonical — transcribe ONCE, reuse forever;
#         $VIDEO_EDITOR_WORK/<job-name>/ (default /tmp/video-editor/<job-name>/) is just render scratch)
#
# --diarize adds speaker labels per word (requires HUGGINGFACE_TOKEN in env or in the kit's
# .env; whisperx 3.8's default pyannote/speaker-diarization-community-1 must be accepted on
# Hugging Face).
#
# A second voice on a phone speaker (about 10 dB under the host) goes missing from the text, and
# wav2vec2 then force-fits the host's next words over its window. Two knobs, both unset = WhisperX's
# own defaults, both apply only to a fresh transcription (a reuse of the canonical refuses them),
# and neither is a fix (measured on three reference phone-call jobs, 2026-09-23): each moves WHERE Whisper
# drops the quiet voice, so `cut-audit.py --coverage` still gates and realign-spans.py still repairs.
#   --chunk-size N (env WHISPERX_CHUNK_SIZE; 1-30 s, default 30) caps how much VAD-merged speech
#     Whisper decodes as one window. Where the VAD FOUND the AI's lines and Whisper dropped them
#     inside a 30 s window shared with the louder host, 20 recovered them; on a whole 53-minute
#     call it dropped other AI lines the default had kept. Below 20 it invented words in room tone.
#   --vad-onset X --vad-offset Y (env VAD_ONSET / VAD_OFFSET) set the pyannote speech thresholds,
#     together, offset <= onset (defaults 0.500 / 0.363), for a voice the VAD itself scores low.
# The flags win over the env.
#
# Per-clip failures that are a property of the FOOTAGE, not of the machine (2026-09-25): a clip
# with no audio stream (QuickTime screen recording), with no speech, or whose detected language
# has no wav2vec2 aligner is written to words.json as a zero-word entry
#   {"clip", "file", "path", "duration", "language", "no_speech": true, "reason", "words": []}
# and the run continues. It used to abort the whole job and lose every other clip's transcript.

set -euo pipefail

# Windows pipes default python stdio to cp1252, which can't encode the ⚠/→ glyphs in the
# long-span warnings (or huggingface's progress output), so force UTF-8 everywhere.
# Windows without Developer Mode also denies os.symlink (WinError 1314): a real first-run
# large-v3 download crashed on that (2026-08-13). HF_HUB_DISABLE_SYMLINKS makes
# huggingface_hub copy instead of symlink, but treat it as belt-and-suspenders, NOT the
# proven fix: whisperx pins huggingface-hub <1.0, which never reads this var (only hub
# >=1.0 does) and whose cache already copy-degrades on denied symlinks. The likelier root
# cure for that crash is the uv interpreter pre-install below (junction race). If 1314
# recurs on a fresh no-Developer-Mode box, capture the traceback to find the real symlink
# site. Windows-only; costs disk, never correctness. No-ops on macOS/Linux.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) export HF_HUB_DISABLE_SYMLINKS=1 ;; esac

# ─ Hardware auto-detect: an NVIDIA GPU (Windows/Linux) runs WhisperX on CUDA,
# several times faster than CPU. Apple Silicon stays CPU int8 (the lock: MPS
# torch is still flaky for some ops; CPU is slower but never silently wrong).
# WHISPERX_DEVICE=cpu|cuda overrides the auto-pick. The python side runs a full
# fallback ladder (cuda float16 → cuda int8_float16 → cpu int8), so a broken
# CUDA stack degrades to CPU with a warning; it can never block an edit.
GPU=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then GPU=1; fi
DEVICE="${WHISPERX_DEVICE:-}"
if [ -z "$DEVICE" ]; then
  if [ "$GPU" -eq 1 ]; then DEVICE=cuda; else DEVICE=cpu; fi
fi

PREFETCH=0
for _a in "$@"; do [ "$_a" = "--prefetch" ] && PREFETCH=1; done
USAGE="usage: transcribe.sh <job_dir> [--diarize] [--force] [--lang <code>] [--chunk-size N] [--vad-onset X --vad-offset Y]
       transcribe.sh --file <audio|video> --out <words.json> [--diarize] [--lang <code>] [--chunk-size N] [--vad-onset X --vad-offset Y]
       transcribe.sh --prefetch [--lang <code>]"
JOB_DIR=""
if [ "$PREFETCH" -eq 0 ]; then
  case "${1:-}" in
    --file|--out) ;;
    *) JOB_DIR="${1:?$USAGE}"; shift ;;
  esac
fi

DIARIZE=0
FORCE=0
FILE=""
OUT=""
CHUNK_SIZE="${WHISPERX_CHUNK_SIZE:-}"
VAD_ONSET="${VAD_ONSET:-}"
VAD_OFFSET="${VAD_OFFSET:-}"
LANG_PICK="${WHISPERX_LANG:-auto}"
LANG_GIVEN=0; [ -n "${WHISPERX_LANG:-}" ] && LANG_GIVEN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --prefetch) ;;
    --diarize) DIARIZE=1 ;;
    --force)   FORCE=1 ;;
    --lang)    shift; LANG_PICK="${1:?--lang needs a code, e.g. es}"; LANG_GIVEN=1 ;;
    --lang=*)  LANG_PICK="${1#--lang=}"; LANG_GIVEN=1 ;;
    --file)       FILE="${2:?--file needs a path}"; shift ;;
    --out)        OUT="${2:?--out needs a path}"; shift ;;
    --chunk-size) CHUNK_SIZE="${2:?--chunk-size needs a value}"; shift ;;
    --vad-onset)  VAD_ONSET="${2:?--vad-onset needs a value}"; shift ;;
    --vad-offset) VAD_OFFSET="${2:?--vad-offset needs a value}"; shift ;;
    *) echo "unknown flag: $1" >&2; echo "$USAGE" >&2; exit 1 ;;
  esac
  shift
done

# Whisper hears 30 s at a time: a longer window would be cut short, so 30 is the ceiling.
if [ -n "$CHUNK_SIZE" ]; then
  if ! [[ "$CHUNK_SIZE" =~ ^[0-9]+$ ]] || [ "$CHUNK_SIZE" -lt 1 ] || [ "$CHUNK_SIZE" -gt 30 ]; then
    echo "--chunk-size is whole seconds from 1 to 30, got '$CHUNK_SIZE'" >&2; exit 1
  fi
fi
# The two thresholds go together: an onset lowered alone under the default offset (0.363)
# would close every speech region on the frame after it opens.
if [ -n "$VAD_ONSET$VAD_OFFSET" ]; then
  if [ -z "$VAD_ONSET" ] || [ -z "$VAD_OFFSET" ]; then
    echo "--vad-onset and --vad-offset (VAD_ONSET / VAD_OFFSET) are set together" >&2; exit 1
  fi
  for v in "$VAD_ONSET" "$VAD_OFFSET"; do
    [[ "$v" =~ ^0?\.[0-9]+$ ]] || { echo "a VAD threshold is a fraction like 0.3, got '$v'" >&2; exit 1; }
  done
  awk -v on="$VAD_ONSET" -v off="$VAD_OFFSET" 'BEGIN { exit !(off + 0 <= on + 0) }' \
    || { echo "--vad-offset ($VAD_OFFSET) must not exceed --vad-onset ($VAD_ONSET)" >&2; exit 1; }
fi

# ONE scratch root for the shell scripts AND their python helpers (2026-09-25). Git Bash maps
# /tmp to %TEMP%, but native Windows Python resolves "/tmp/video-editor" to C:\tmp\video-editor,
# so splice.sh and polish-boundaries.py read and wrote DIFFERENT folders on Windows. The root is
# VIDEO_EDITOR_WORK if set, else /tmp/video-editor; on Windows it is exported as a mixed path
# (C:/Users/.../Temp/video-editor) that bash and Python both resolve to the same folder.
WORK_ROOT="${VIDEO_EDITOR_WORK:-/tmp/video-editor}"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*)
  command -v cygpath >/dev/null 2>&1 && WORK_ROOT="$(cygpath -m "$WORK_ROOT")" ;;
esac
export VIDEO_EDITOR_WORK="$WORK_ROOT"
CANON=""
if [ "$PREFETCH" -eq 1 ]; then
  JOB_NAME="_prefetch"; MEDIA_DIR=""
  WORK="$WORK_ROOT/$JOB_NAME"
elif [ -n "$FILE$OUT" ]; then
  # Standalone form: never a job folder's transcript/, so nothing canonical is read or replaced.
  if [ -n "$JOB_DIR" ] || [ -z "$FILE" ] || [ -z "$OUT" ]; then echo "$USAGE" >&2; exit 1; fi
  [ -f "$FILE" ] || { echo "no such file: $FILE" >&2; exit 1; }
  FILE="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
  mkdir -p "$(dirname "$OUT")"
  OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
  JOB_NAME="transcribe-file"
  WORK="$WORK_ROOT/$JOB_NAME"
  CLIPS=("$FILE")
  PY_OUT="$OUT"
else
  JOB_DIR="$(cd "$JOB_DIR" && pwd)"
  JOB_NAME="$(basename "$JOB_DIR")"
  MEDIA_DIR="$JOB_DIR"
  [ -d "$JOB_DIR/raw" ] && MEDIA_DIR="$JOB_DIR/raw"
  WORK="$WORK_ROOT/$JOB_NAME"
  CANON="$JOB_DIR/transcript/words.json"   # persisted canonical transcript — transcribe ONCE, reuse forever
  mkdir -p "$JOB_DIR/transcript"
  PY_OUT="$WORK/words.json"
fi
mkdir -p "$WORK"

# v1.3: no --lang / WHISPERX_LANG → the creator's profile `idioma` (profile.py returns "auto" with no
# profile, so v1.2 behaviour is unchanged). Any failure reading it → auto, silently.
KIT_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
if [ "$LANG_GIVEN" -eq 0 ]; then
  P_LANG="$(python3 "$KIT_ROOT/workflows/profile.py" get idioma 2>/dev/null | tr -d '\r[:space:]' | tr '[:upper:]' '[:lower:]' || true)"
  if [ -n "$P_LANG" ] && [ "$P_LANG" != "auto" ] && printf '%s' "$P_LANG" | grep -Eq '^[a-z]{2,3}$'; then
    LANG_PICK="$P_LANG"
    echo "[transcribe] language $LANG_PICK from the creator's style profile (override: --lang auto)" >&2
  fi
fi

# A background prefetch builds the SAME venv: a transcription started meanwhile would see no .deps-ok and
# rm -rf the half-built venv under it. Wait for it instead; a second prefetch just reports and leaves.
PREFETCH_PID="$WORK_ROOT/_prefetch/prefetch.pid"
if [ -f "$PREFETCH_PID" ] && kill -0 "$(cat "$PREFETCH_PID" 2>/dev/null || echo 0)" 2>/dev/null \
   && [ "$(cat "$PREFETCH_PID")" != "$$" ]; then
  if [ "$PREFETCH" -eq 1 ]; then
    echo "[transcribe] prefetch already running (pid $(cat "$PREFETCH_PID")); log: $WORK_ROOT/_prefetch/prefetch.log" >&2
    exit 0
  fi
  echo "[transcribe] waiting for the background model download (prefetch) to finish…" >&2
  while kill -0 "$(cat "$PREFETCH_PID" 2>/dev/null || echo 0)" 2>/dev/null; do sleep 5; done
fi

if [ "$PREFETCH" -eq 1 ]; then
  echo "$$" > "$PREFETCH_PID"
  trap 'rm -f "$PREFETCH_PID"' EXIT
  PREFETCH_LOG="$WORK/prefetch.log"
  PREFETCH_LANG="$LANG_PICK"; [ "$PREFETCH_LANG" = "auto" ] && PREFETCH_LANG=es
  echo "[transcribe] prefetch: whisperx venv + large-v3 + aligner ($PREFETCH_LANG); log: $PREFETCH_LOG" >&2
  echo "=== prefetch $(date '+%Y-%m-%d %H:%M:%S') lang=$PREFETCH_LANG ===" >>"$PREFETCH_LOG"
  # everything from here on (venv build, downloads) goes to the log; the verdict is repeated on the terminal
  exec 3>&2 2>>"$PREFETCH_LOG" 1>&2
fi

if [ "$PREFETCH" -eq 0 ] && [ -n "$CANON" ]; then

# Transcribe ONCE. WhisperX large-v3 is slow + deterministic, so a persisted canonical
# transcript wins unless --force. This is the single source of truth for the whole
# pipeline (rough cut AND finishing captions) — nothing else transcribes this footage.
if [ "$FORCE" -eq 0 ] && [ -f "$CANON" ]; then
  if [ -n "$VAD_ONSET$CHUNK_SIZE" ]; then
    # A reuse would silently drop the settings the caller asked for.
    echo "[transcribe] $CANON exists: --chunk-size / the VAD thresholds apply only to a fresh transcription;" >&2
    echo "[transcribe]   add --force to re-transcribe with them, or unset them to reuse it" >&2
    exit 1
  fi
  echo "[transcribe] reusing canonical transcript $CANON (pass --force to re-transcribe)" >&2
  cp "$CANON" "$WORK/words.json"
  echo "$WORK/words.json"
  exit 0
fi

shopt -s nullglob nocaseglob
CLIPS=()
for f in "$MEDIA_DIR"/*.mov "$MEDIA_DIR"/*.mp4 "$MEDIA_DIR"/*.mkv "$MEDIA_DIR"/*.m4v; do
  # workflows/normalize-source.py writes <stem>.normalizing.mov next to the clips while it
  # runs (and moves originals into raw/_source/, which this flat glob never enters): an
  # in-progress temp file is not footage (2026-09-25).
  case "$(basename "$f")" in .*|*.normalizing.*) continue ;; esac
  [ -f "$f" ] && CLIPS+=("$f")
done
shopt -u nocaseglob
if [ ${#CLIPS[@]} -eq 0 ]; then
  echo "no clips found in $MEDIA_DIR" >&2
  exit 1
fi
fi   # job mode: canonical reuse and the clip list

# (2026-09-25) The old block here prepended /opt/homebrew/opt/ffmpeg@7 to PATH and
# DYLD_LIBRARY_PATH whenever that keg existed. Nothing documented why; the only consumer of
# FFmpeg 4-7 *libraries* in this venv is torchcodec, which pyannote imports but this pipeline
# never decodes with (whisperx.load_audio shells out to the ffmpeg CLI, and diarization is handed
# an in-memory waveform). On a buyer's Mac it silently swapped the ffmpeg binary that decodes
# the audio for an older one. Removed; the torchcodec load warning it was probably chasing is
# filtered in the python part below instead.

# Tested stack, pinned (2026-09-25). An unpinned `whisperx` gave every future buyer whatever
# PyPI had that day, untested. whisperx 3.8.6 requires torch~=2.8.0 / torchaudio~=2.8.0;
# `uv pip compile` resolves exactly torch 2.8.0, torchaudio 2.8.0, torchvision 0.23.0,
# torchcodec 0.7.0, pyannote-audio 4.0.7 on macOS arm64, Windows x64 and Linux x64 (verified
# 2026-09-25; the owner's working venv holds the same versions). Bump these together, after a
# real transcription test, never one alone.
WHISPERX_PIN="3.8.6"
TORCH_PIN="2.8.0"
EXTRA_PINS=()
# Intel Macs (2026-09-29): PyTorch publishes no macOS x86_64 wheel after 2.2.2, so whisperx 3.8.6 (torch~=2.8)
# cannot install there at all. `uv pip compile` for x86_64-apple-darwin resolves whisperx 3.3.1 → torch 2.2.2,
# faster-whisper 1.1.0, ctranslate2 4.3.1, pyannote.audio 3.3.2; today's PyPI then also needs numpy<2 (torch 2.2
# wheels are built against NumPy 1), transformers<4.46 (newer ones switch torch off below 2.5) and matplotlib
# (pyannote 3.3.2 imports it). Verified importing on x86_64 under Rosetta. A Rosetta shell on an Apple Silicon
# Mac is NOT an Intel Mac: sysctl.proc_translated=1 keeps the native arm64 stack. VE_WHISPERX_STACK=intel forces it.
if [ "${VE_WHISPERX_STACK:-}" = intel ] || { [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = x86_64 ] \
     && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" != 1 ]; }; then
  WHISPERX_PIN="3.3.1"
  TORCH_PIN="2.2.2"
  EXTRA_PINS=("numpy<2" "transformers<4.46" "matplotlib")
  INTEL_STACK=1
fi

# Persistent venv: built once, reused every run. whisperx pulls torch, so it
# gets its own box — it can't share the faster-whisper venv (different deps).
VENV="${VIDEO_EDITOR_WHISPERX_VENV:-$HOME/.cache/video-editor/whisperx-venv}"
# venv layout differs by OS: bin/python (macOS/Linux) vs Scripts/python.exe (Windows)
venv_py() { if [ -e "$VENV/Scripts/python.exe" ]; then echo "$VENV/Scripts/python.exe"; else echo "$VENV/bin/python"; fi; }
# sentinel written only after a successful install — a half-built venv (install
# interrupted once) self-heals on the next run instead of wedging forever
if [ ! -e "$VENV/.deps-ok" ]; then
  echo "[transcribe] first-run: building whisperx venv at $VENV (pulls torch, ~minutes)" >&2
  rm -rf "$VENV"
  # Windows: materialize the managed interpreter BEFORE creating the venv. `uv venv
  # --python 3.11` can trigger a just-in-time CPython download whose junction/trampoline
  # finalization races the venv creation and yields a broken venv (hit on a real machine,
  # 2026-08-13). A separate install step is idempotent and instant when already present.
  # Its output goes to a log: on a healthy box it still prints "Missing expected target
  # directory for Python minor version link" (a client box, 2026-09-07), which reads as an
  # error to someone watching the first run and is nothing; the venv step is the real check.
  case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*)
    echo "[transcribe] ensuring a managed Python 3.11 (uv; log: $WORK/uv-python-install.log)" >&2
    uv python install 3.11 >"$WORK/uv-python-install.log" 2>&1 \
      || echo "[transcribe] · uv python install 3.11 reported a problem (see the log); the venv step below is the real check" >&2
    ;;
  esac
  if ! uv venv "$VENV" --python 3.11 >&2; then
    echo "[transcribe] venv creation failed; retrying once from clean" >&2
    rm -rf "$VENV"
    uv venv "$VENV" --python 3.11 >&2
  fi
  uv pip install --python "$(venv_py)" "whisperx==$WHISPERX_PIN" "torch==$TORCH_PIN" "torchaudio==$TORCH_PIN" \
      ${EXTRA_PINS[@]+"${EXTRA_PINS[@]}"} >&2
  # record what this venv was VERIFIED for; the CUDA step below upgrades it in place
  echo cpu > "$VENV/.mode"
  touch "$VENV/.deps-ok"
fi
# Intel stack: torch 2.2.2 and ctranslate2 4.3.1 each ship their OWN copy of Intel's OpenMP runtime, libiomp5 (torch's in
# functorch/.dylibs and torch/lib, 5.0.20220623; ctranslate2's in ctranslate2/.dylibs, 5.0.20221004). Two copies in one
# process crashed (segfault under Rosetta) or stalled (the Intel CI Mac: no progress for 2 h) as soon as the VAD (torch)
# and the ASR (ctranslate2) ran together, 2026-09-29; KMP_DUPLICATE_LIB_OK only silenced the warning about it. Every
# copy now points at ctranslate2's, the newest, so dyld loads ONE runtime (DYLD_PRINT_LIBRARIES shows one libiomp5) and
# the Spanish test clip transcribes. Every run, so a venv an older kit built is repaired too; the originals stay as .orig.
if [ "${INTEL_STACK:-0}" = 1 ]; then
  IOMP_SP="$("$(venv_py)" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])' 2>/dev/null)"
  IOMP_KEEP="$IOMP_SP/ctranslate2/.dylibs/libiomp5.dylib"
  if [ -f "$IOMP_KEEP" ] && [ ! -L "$IOMP_KEEP" ]; then
    for IOMP_F in "$IOMP_SP/functorch/.dylibs/libiomp5.dylib" "$IOMP_SP/torch/lib/libiomp5.dylib"; do
      if [ -f "$IOMP_F" ] && [ ! -L "$IOMP_F" ]; then mv "$IOMP_F" "$IOMP_F.orig"; fi
      if [ -e "$IOMP_F.orig" ] && [ "$(readlink "$IOMP_F" 2>/dev/null)" != "$IOMP_KEEP" ]; then ln -sf "$IOMP_KEEP" "$IOMP_F"; fi
    done
  else
    echo "[transcribe] ⚠ Intel stack: ctranslate2's OpenMP runtime not found in $IOMP_SP; two runtimes may load" >&2
  fi
fi
# cuda_torch: make this venv's torch a CUDA build and PROVE it, writing .mode from the
# probe. Used on a fresh build AND to repair a venv that exists but is CPU-only on a GPU
# machine (a venv built before GPU support, or while no GPU was visible): that case used
# to print "rm -rf the venv and re-run" and carry on at CPU speed, so an RTX 5070 box
# with an August venv transcribed on CPU with the GPU reported ready by check-setup
# (2026-09-27). The repair keeps the venv, whisperx and the downloaded models; only
# torch/torchaudio are swapped (~3 GB). A repair that fails leaves .cuda-tried so it is
# not re-attempted (and re-downloaded) on every run; delete that file to retry.
cuda_torch() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      # PyPI torch on Windows is CPU-only; swap in the CUDA build (Linux PyPI
      # wheels already ship CUDA, so only Windows needs this). cu128 wheels
      # want a current NVIDIA driver (and are the first to run Blackwell, RTX 50xx);
      # if this install or the runtime probe fails, everything falls back to CPU
      # and the edit still runs.
      #
      # whisperx installed the CPU torch, and a plain `uv pip install torch
      # --index-url <cu128>` on top is a NO-OP: the requirement is already satisfied,
      # so uv never consults the CUDA index, exits 0 ("Checked 2 packages"), and the
      # venv keeps CPU torch while .mode said cuda (a client RTX 3060 ran CPU-only for
      # exactly that, 2026-09-07). Force the reinstall, pinned to the versions whisperx
      # resolved so torchvision/torchcodec, ABI-matched to that torch, keep working.
      echo "[transcribe] NVIDIA GPU detected: installing CUDA torch (~3 GB, once)" >&2
      read -r -a TORCH_PINS <<< "$("$(venv_py)" -c 'import torch, torchaudio; print("torch==" + torch.__version__.split("+")[0], "torchaudio==" + torchaudio.__version__.split("+")[0])' 2>/dev/null || echo "torch torchaudio")"
      uv pip install --python "$(venv_py)" \
          --reinstall-package torch --reinstall-package torchaudio "${TORCH_PINS[@]}" \
          --index-url https://download.pytorch.org/whl/cu128 >&2 \
        || echo "[transcribe] ⚠ CUDA torch install failed (read the uv output above)" >&2
      ;;
  esac
  # .mode is written from a PROBE, never from intent: the install's exit code proves
  # nothing (above). A venv that says cuda but holds CPU torch would request CUDA and
  # the python ladder would quietly drop to CPU on every run.
  if "$(venv_py)" -c 'import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    echo "[transcribe] ✓ CUDA verified: $("$(venv_py)" -c 'import torch; print(torch.__version__, "on", torch.cuda.get_device_name(0))' 2>/dev/null)" >&2
    echo cuda > "$VENV/.mode"
    rm -f "$VENV/.cuda-tried"
    return 0
  fi
  echo "[transcribe] ⚠ CUDA did not take (torch.cuda.is_available() is False); this venv stays CPU-only." >&2
  echo "[transcribe]   Transcription works, several times slower. GPU retry: rm \"$VENV/.cuda-tried\" and re-run" >&2
  echo "[transcribe]   (an NVIDIA driver too old for cu128 is the usual cause; update it first)." >&2
  echo cpu > "$VENV/.mode"
  touch "$VENV/.cuda-tried"
  return 1
}
if [ "$DEVICE" = cuda ] && [ "$(cat "$VENV/.mode" 2>/dev/null || echo cpu)" != "cuda" ]; then
  if [ -e "$VENV/.cuda-tried" ]; then
    echo "[transcribe] · CUDA requested, but this venv's CUDA torch did not take on an earlier try: CPU." >&2
    echo "[transcribe]   GPU retry: rm \"$VENV/.cuda-tried\" and re-run." >&2
    DEVICE=cpu
  else
    echo "[transcribe] · this WhisperX venv is CPU-only on a GPU machine: upgrading it to CUDA in place" >&2
    cuda_torch || DEVICE=cpu
  fi
fi
PYBIN="$(venv_py)"
# A venv built before the pin (2026-09-25) keeps whatever whisperx it got. Say so once, never
# rebuild on our own: a rebuild is a ~1 GB download the buyer should choose.
HAVE_WX="$("$PYBIN" -c 'import importlib.metadata as m; print(m.version("whisperx"))' 2>/dev/null || echo "?")"
if [ "$HAVE_WX" != "$WHISPERX_PIN" ]; then
  echo "[transcribe] · this venv has whisperx $HAVE_WX; the kit is tested on $WHISPERX_PIN." >&2
  echo "[transcribe]   For the tested stack: rm -rf \"$VENV\" and re-run (rebuilds once)." >&2
fi

# --prefetch: the venv exists now; fetch the two models into the normal caches (no RAM load when cached).
if [ "$PREFETCH" -eq 1 ]; then
  if "$PYBIN" - "$PREFETCH_LANG" <<'PY'
import os, sys, warnings
warnings.filterwarnings("ignore", message=r"\s*torchcodec is not installed correctly", category=UserWarning)
lang = sys.argv[1]
from faster_whisper.utils import download_model
have = []
try:
    download_model("large-v3", local_files_only=True); have.append("large-v3")
except Exception:
    print("[prefetch] downloading large-v3 (~3 GB)…", flush=True)
    download_model("large-v3"); print("[prefetch] ✓ large-v3 downloaded", flush=True)
import torch, torchaudio
from whisperx import alignment
name = alignment.DEFAULT_ALIGN_MODELS_TORCH.get(lang) or alignment.DEFAULT_ALIGN_MODELS_HF.get(lang)
if not name:
    print(f"[prefetch] · no default wav2vec2 aligner for '{lang}' (nothing to fetch)", flush=True)
else:
    cached = False
    if name in torchaudio.pipelines.__all__:
        ck = os.path.join(torch.hub.get_dir(), "checkpoints",
                          os.path.basename(torchaudio.pipelines.__dict__[name]._path))
        cached = os.path.isfile(ck)
    else:
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(name, local_files_only=True); cached = True
        except Exception:
            cached = False
    if cached:
        have.append(f"aligner {lang}")
    else:
        print(f"[prefetch] downloading aligner {name}…", flush=True)
        alignment.load_align_model(language_code=lang, device="cpu")
        print(f"[prefetch] ✓ aligner {lang} downloaded", flush=True)
print("[prefetch] ALREADY_PRESENT: " + ", ".join(have) if have else "[prefetch] nothing was cached", flush=True)
PY
  then
    if tail -n 1 "$PREFETCH_LOG" | grep -q "ALREADY_PRESENT: large-v3, aligner"; then
      echo "[transcribe] ✓ prefetch: whisperx venv, large-v3 and the $PREFETCH_LANG aligner already present" >&3
    else
      echo "[transcribe] ✓ prefetch done: whisperx venv, large-v3 and the $PREFETCH_LANG aligner are ready" >&3
    fi
    exit 0
  fi
  echo "[transcribe] ✗ prefetch failed; see $PREFETCH_LOG" >&3
  exit 1
fi

# --diarize: HUGGINGFACE_TOKEN from the environment first, else from the kit's .env (the file
# .env.example tells buyers to create). The scripts never sourced it, so a buyer who followed
# the setup doc still hit "requires HUGGINGFACE_TOKEN" (2026-09-25). Only that one key is read,
# the file is never executed.
if [ "$DIARIZE" -eq 1 ] && [ -z "${HUGGINGFACE_TOKEN:-}" ]; then
  KIT_ENV="$(cd "$(dirname "$0")/../../../.." && pwd)/.env"
  if [ -f "$KIT_ENV" ]; then
    HF_LINE="$(grep -E '^[[:space:]]*(export[[:space:]]+)?(HUGGINGFACE_TOKEN|HF_TOKEN)[[:space:]]*=' "$KIT_ENV" | tail -n 1 || true)"
    HF_VAL="${HF_LINE#*=}"
    HF_VAL="$(printf '%s' "$HF_VAL" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")"
    if [ -n "$HF_VAL" ]; then
      export HUGGINGFACE_TOKEN="$HF_VAL"
      echo "[transcribe] HUGGINGFACE_TOKEN loaded from $KIT_ENV" >&2
    fi
  fi
fi

"$PYBIN" - "$PY_OUT" "$DIARIZE" "$DEVICE" "$LANG_PICK" "$CHUNK_SIZE" "$VAD_ONSET" "$VAD_OFFSET" "${CLIPS[@]}" <<'PY'
import json, math, os, subprocess, sys, warnings
# pyannote (imported by whisperx for VAD) tries to load torchcodec at import time and, when the
# system FFmpeg is not 4-7 (Homebrew ships 8+ now), prints a ~30-line "Could not load
# libtorchcodec ... libavutil" traceback. It is harmless here: nothing in this pipeline decodes
# through torchcodec (whisperx.load_audio uses the ffmpeg CLI; diarization gets an in-memory
# waveform). It read as a crash to every buyer on the first run (clean-install test,
# 2026-09-25). Filter exactly that UserWarning by its message; every other warning and every
# real error still prints, and pyannote still raises if anything ever asks torchcodec to decode.
warnings.filterwarnings("ignore", message=r"\s*torchcodec is not installed correctly",
                        category=UserWarning)
import whisperx

out_path = sys.argv[1]
diarize_flag = sys.argv[2] == "1"
want_device = sys.argv[3]      # "cuda" or "cpu", decided by transcribe.sh
lang_pick = sys.argv[4].strip().lower()   # "auto" or an ISO code, decided by transcribe.sh
# Validated by transcribe.sh; empty = WhisperX's own defaults (no chunk_size, vad_options None).
chunk_kw = {"chunk_size": int(sys.argv[5])} if sys.argv[5] else {}
vad_options = ({"vad_onset": float(sys.argv[6]), "vad_offset": float(sys.argv[7])}
               if sys.argv[6] else None)
clip_paths = sys.argv[8:]
if chunk_kw:
    print(f"[transcribe] Whisper window (chunk size) {chunk_kw['chunk_size']} s (WhisperX default 30)",
          file=sys.stderr)
if vad_options:
    print(f"[transcribe] VAD onset {vad_options['vad_onset']} / offset {vad_options['vad_offset']} "
          "(WhisperX defaults 0.500 / 0.363)", file=sys.stderr)

# Device ladder. CPU int8 is the always-works floor (and the Apple Silicon
# lock: MPS torch is still spotty for some ops; CPU is slower but never
# silently wrong). With an NVIDIA GPU the ladder tries float16 first, then
# int8_float16 (fits ~4 GB cards), then drops to CPU: a broken CUDA stack
# (old driver, missing cuDNN, OOM) must never block an edit.
tiers = [("cpu", "int8", 8)]
if want_device == "cuda":
    tiers = [("cuda", "float16", 16), ("cuda", "int8_float16", 16)] + tiers
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError(
                "torch.cuda.is_available() is False (CPU-only torch build, or the "
                "NVIDIA driver is too old for this CUDA runtime; a driver update "
                "usually fixes it)")
        # Windows: ctranslate2 resolves cublas/cudnn DLLs by name from the DLL
        # search path, and the CUDA torch wheel bundles them in torch/lib.
        if os.name == "nt":
            _lib = os.path.join(os.path.dirname(torch.__file__), "lib")
            if os.path.isdir(_lib):
                os.add_dll_directory(_lib)
                os.environ["PATH"] = _lib + os.pathsep + os.environ.get("PATH", "")
        print(f"[transcribe] NVIDIA GPU: {torch.cuda.get_device_name(0)}", file=sys.stderr)
    except Exception as e:
        # Loud on purpose: a correct transcript at several times the cost is the failure
        # mode nobody reports (the trap a client RTX 3060 sat in, 2026-09-07).
        print("[transcribe] " + "!" * 66, file=sys.stderr)
        print(f"[transcribe] ⚠ SLOW PATH: CUDA unavailable ({e}); using CPU int8.", file=sys.stderr)
        print("[transcribe]   This venv was verified for CUDA when built, and the GPU is not reachable now.", file=sys.stderr)
        print("[transcribe]   Fix the NVIDIA driver, or rm -rf the venv and re-run so the rebuild re-verifies CUDA.", file=sys.stderr)
        print("[transcribe] " + "!" * 66, file=sys.stderr)
        tiers = [("cpu", "int8", 8)]

# None = let large-v3 detect the language of each clip; a code pins it for every clip.
LANG = None if lang_pick in ("", "auto") else lang_pick
_align_cache = {}

def align_for(lang, device):
    """wav2vec2 alignment model for one language, loaded once (downloads on first use)."""
    key = (lang, device)
    if key not in _align_cache:
        print(f"[transcribe] loading wav2vec2 alignment model ({lang})", file=sys.stderr)
        _align_cache[key] = whisperx.load_align_model(language_code=lang, device=device)
    return _align_cache[key]

def no_aligner(e):
    """True when load_align_model failed because wav2vec2 has no model for the language
    (a property of the footage), not because of the machine (network, disk, torch)."""
    return isinstance(e, ValueError) and "align-model" in str(e)

def load_stack(device, compute_type):
    print(f"[transcribe] loading whisperx large-v3 ({device}, {compute_type}, "
          f"language={LANG or 'auto-detect'})", file=sys.stderr)
    asr = whisperx.load_model("large-v3", device, compute_type=compute_type, language=LANG,
                              vad_options=vad_options)
    _align_cache.clear()
    align = meta = None   # auto-detect: picked per clip, after detection
    if LANG:
        try:
            align, meta = align_for(LANG, device)
        except Exception as e:
            # a forced language with no aligner is recorded per clip (no_speech entry),
            # it must not read as a device failure and walk the CUDA -> CPU ladder
            if not no_aligner(e):
                raise
            print(f"[transcribe] ⚠ no wav2vec2 aligner for forced language {LANG!r}; "
                  "clips will be recorded without words", file=sys.stderr)
    return asr, align, meta

for i, (device, compute_type, batch_size) in enumerate(tiers):
    try:
        asr_model, align_model, align_metadata = load_stack(device, compute_type)
        break
    except Exception as e:
        if i == len(tiers) - 1:
            raise
        nd, nc, _ = tiers[i + 1]
        print(f"[transcribe] ⚠ {device}/{compute_type} failed to load "
              f"({type(e).__name__}: {e}); trying {nd}/{nc}", file=sys.stderr)

def load_diarize(device):
    hf_token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    if not hf_token:
        print("[transcribe] --diarize requires HUGGINGFACE_TOKEN (env, or the kit's .env)",
              file=sys.stderr)
        sys.exit(1)
    print("[transcribe] loading pyannote diarization pipeline", file=sys.stderr)
    # whisperx 3.8 moved the pipeline to whisperx.diarize and renamed use_auth_token to token;
    # the old top-level whisperx.DiarizationPipeline(use_auth_token=...) is an AttributeError
    # there, so --diarize crashed on the pinned stack (2026-09-25). The old spelling stays as a
    # fallback for a venv built before the pin.
    try:
        from whisperx.diarize import DiarizationPipeline
        return DiarizationPipeline(token=hf_token, device=device)
    except (ImportError, TypeError):
        return whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)

diarize_model = load_diarize(device) if diarize_flag else None

class ClipSkip(Exception):
    """A clip that cannot yield words for a reason in the FOOTAGE (no audio stream, no speech,
    no aligner for its language). Recorded as a no_speech entry; never aborts the run and never
    triggers the CUDA -> CPU fallback (that one is for machine failures)."""
    def __init__(self, reason, language=None, text=""):
        super().__init__(reason)
        self.reason, self.language, self.text = reason, language, text

def probe(path):
    """(has_audio, container duration) via ffprobe; duration None when unreadable."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout or "{}")
    except ValueError:
        d = {}
    has_audio = any(s.get("codec_type") == "audio" for s in d.get("streams", []))
    try:
        dur = float(d.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        dur = None
    return has_audio, dur

def _finite(x):
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False

def interpolate_unaligned(segments, duration):
    """Give every word wav2vec2 could not align real, non-overlapping times.

    wav2vec2's character set has no digits or symbols, so "137", "2026" or "%" in Spanish
    come back with no timestamps. The old loop DROPPED those words (the transcript lost every
    price and year), and whisperx 3.8's own fallback copies the NEAREST aligned word's times,
    which stacks the number on top of its neighbour with no score (it then read as a p1.0
    word). An aligned word is one with a finite start, end AND score; every other word gets
    the gap between its aligned neighbours (same sentence first, else the sentence bounds,
    never crossing an aligned word anywhere in the clip), split in proportion to character
    length, and is marked interpolated with prob 0.0 so polish/refine treat its timing as
    untrusted (2026-09-25)."""
    flat = [(si, w) for si, seg in enumerate(segments) for w in seg.get("words", [])]
    good = [_finite(w.get("start")) and _finite(w.get("end")) and _finite(w.get("score"))
            for _, w in flat]
    n, k, fixed = len(flat), 0, 0
    while k < n:
        if good[k]:
            k += 1
            continue
        si = flat[k][0]
        j = k
        while j < n and not good[j] and flat[j][0] == si:
            j += 1
        seg = segments[si]
        prev_g = next((flat[q][1] for q in range(k - 1, -1, -1) if good[q]), None)
        next_g = next((flat[q][1] for q in range(j, n) if good[q]), None)
        g_lo = float(prev_g["end"]) if prev_g else 0.0
        g_hi = float(next_g["start"]) if next_g else float(duration)
        same_prev = k > 0 and good[k - 1] and flat[k - 1][0] == si
        same_next = j < n and good[j] and flat[j][0] == si
        lo = float(flat[k - 1][1]["end"]) if same_prev else \
            (float(seg["start"]) if _finite(seg.get("start")) else g_lo)
        hi = float(flat[j][1]["start"]) if same_next else \
            (float(seg["end"]) if _finite(seg.get("end")) else g_hi)
        lo, hi = max(lo, g_lo), min(hi, g_hi)
        if hi < lo:
            hi = lo
        run = [flat[q][1] for q in range(k, j)]
        weights = [max(1, len(str(w.get("word", "")).strip())) for w in run]
        tot, acc = float(sum(weights)), 0
        for w, wt in zip(run, weights):
            w["start"] = lo + (hi - lo) * acc / tot
            acc += wt
            w["end"] = lo + (hi - lo) * acc / tot
            w["score"] = 0.0
            w["_interpolated"] = True
            fixed += 1
        k = j
    return fixed

def process(path):
    has_audio, cdur = probe(path)
    if not has_audio:
        raise ClipSkip("no audio stream (e.g. a screen recording without a mic)")
    audio = whisperx.load_audio(path)
    tr = asr_model.transcribe(audio, batch_size=batch_size, language=LANG, **chunk_kw)
    lang = (tr.get("language") or LANG or "en").lower()
    how = "forced" if LANG else "auto-detected"
    print(f"[transcribe] language: {lang} ({how})", file=sys.stderr)
    segs = [s for s in tr.get("segments", []) if str(s.get("text", "")).strip()]
    if not segs:
        raise ClipSkip("no speech detected", lang)
    try:
        am, meta = align_for(lang, device)
    except Exception as e:
        if not no_aligner(e):
            raise
        text = " ".join(str(s.get("text", "")).strip() for s in segs)
        raise ClipSkip(f"no wav2vec2 aligner for language '{lang}' (word timestamps "
                       "impossible; force a language with --lang if detection was wrong)",
                       lang, text)
    al = whisperx.align(
        segs, am, meta, audio, device,
        return_char_alignments=False)
    al["language"] = lang
    fixed = interpolate_unaligned(al.get("segments", []), len(audio) / 16000.0)
    if fixed:
        print(f"[transcribe] {fixed} unalignable word(s) (numbers/symbols) given interpolated "
              "times", file=sys.stderr)
    if diarize_model is not None:
        al = whisperx.assign_word_speakers(diarize_model(audio), al)
    return audio, al

def skipped_entry(name, path, sk):
    _, cdur = probe(path)
    print(f"[transcribe] ⚠ {name}: {sk.reason} — recorded with no words, continuing",
          file=sys.stderr)
    entry = {"clip": name, "file": name, "path": path,
             "duration": round(cdur, 3) if cdur is not None else None,
             "language": sk.language, "no_speech": True, "reason": sk.reason, "words": []}
    if sk.text:
        entry["text"] = sk.text
    return entry

result = {"clips": []}
for path in clip_paths:
    name = os.path.basename(path)
    print(f"[transcribe] {name}", file=sys.stderr)
    try:
        audio, aligned = process(path)
    except ClipSkip as sk:
        result["clips"].append(skipped_entry(name, path, sk))
        continue
    except Exception as e:
        # CUDA can also die mid-run (OOM on a long clip, a cuDNN kernel error):
        # rebuild the whole stack on CPU once and redo this clip. CPU errors
        # are real errors and still raise.
        if device == "cpu":
            raise
        print(f"[transcribe] ⚠ CUDA failed mid-run on {name} "
              f"({type(e).__name__}: {e}); falling back to CPU int8", file=sys.stderr)
        device, compute_type, batch_size = "cpu", "int8", 8
        asr_model, align_model, align_metadata = load_stack(device, compute_type)
        if diarize_flag:
            diarize_model = load_diarize(device)
        try:
            audio, aligned = process(path)
        except ClipSkip as sk:
            result["clips"].append(skipped_entry(name, path, sk))
            continue
    duration = len(audio) / 16000.0

    words = []
    for seg in aligned.get("segments", []):
        for w in seg.get("words", []):
            # interpolate_unaligned() gave every unalignable token (numerals, symbols) real
            # times; this guard only catches a whisperx change that returns a word with none.
            if not (_finite(w.get("start")) and _finite(w.get("end"))):
                continue
            entry = {
                "w": str(w.get("word", "")).strip(),
                "start": round(float(w["start"]), 3),
                "end": round(float(w["end"]), 3),
                "prob": round(float(w.get("score", 1.0)), 3),
            }
            if w.get("_interpolated"):
                entry["interpolated"] = True
            if "speaker" in w:
                entry["speaker"] = w["speaker"]
            words.append(entry)

    result["clips"].append({
        "clip": name,
        "path": path,
        "duration": round(duration, 3),
        "language": aligned.get("language"),
        "words": words,
    })

with open(out_path, "w") as f:
    json.dump(result, f, indent=2)
print(f"[transcribe] wrote {out_path}", file=sys.stderr)

# WhisperX collapses an immediately repeated word into ONE long-span entry —
# the transcript shows a single word but the audio has every utterance. Flag
# them so cut authoring doesn't trust the span (splice's refiner auto-snaps
# these at segment boundaries; MID-segment ones need an authored split).
# A LOW-PROBABILITY word is flagged at half the span: the aligner stretches an uncertain word
# across the silence next to it (your-job 2026-09-04: a p0.35 "the" spanned 0.94 s over a
# 0.9 s pause, under the 1.0 s flag, and the pause shipped inside a segment).
for c in result["clips"]:
    for w in c["words"]:
        span = w["end"] - w["start"]
        if span > 1.0 or (span > 0.5 and w["prob"] < 0.5):
            why = ("possible merged repeat" if span > 1.0
                   else f"low-prob (p{w['prob']:.2f}) word stretched over a pause")
            if w.get("interpolated"):
                why = "unalignable token, times INTERPOLATED across the gap"
            print(f"[transcribe] ⚠ long-span word {w['w']!r} "
                  f"{w['start']:.2f}-{w['end']:.2f} ({span:.2f}s) "
                  f"— {why}, check the audio before keeping",
                  file=sys.stderr)
PY

if [ -n "$FILE" ]; then
  echo "$OUT"
  exit 0
fi

# Persist the canonical copy so we never transcribe this footage again.
cp "$WORK/words.json" "$CANON"
echo "[transcribe] persisted canonical transcript → $CANON" >&2
echo "$WORK/words.json"
