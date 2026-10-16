#!/usr/bin/env python3
"""audio-qa.py <job_dir> — post-splice audio self-check (advisory, never fails the build).

Scans the freshly spliced output for the two artifact classes that have actually shipped:
  1. JOINT CLICKS — step discontinuities at segment butt-joins. The splice applies 5 ms
     edge declick fades, so any joint that still spikes means a regression (or a source
     transient landing exactly on a boundary — inspect by ear).
  2. LIMITER PRESSURE — how hard the -6 dBFS brickwall is working. A static gain that
     drives sustained speech into the ceiling ducks the surrounding audio (5 ms attack /
     50 ms release) — audible as tiny "swallows" on stressed words. If pressure is high,
     the gain came from voice-gain.py's -17 LUFS target, which deliberately runs the
     limiter hard (2026-09-03); only act on this if it is audible, with AMPLIFY_DB
     two under the measured number, and compare by ear.

Stdlib only (no numpy). Reads outputs/<job>.mp4 + transcript/cuts.json.
"""
import array, json, math, os, statistics, subprocess, sys
# Windows consoles/pipes default to cp1252, which can't encode the ⚠/✓ glyphs in this
# script's status lines: a cosmetic print must never kill a pipeline step (it did once,
# 2026-08-13, mid-splice on a real Windows job). Force UTF-8; no-op on macOS/Linux.
for _s in (sys.stdout, sys.stderr):
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

SR = 48000
job_dir = os.path.abspath(sys.argv[1])
job = os.path.basename(job_dir)
out_mp4 = os.path.join(job_dir, "outputs", f"{job}.mp4")
cuts_p = os.path.join(job_dir, "transcript", "cuts.json")
if not (os.path.exists(out_mp4) and os.path.exists(cuts_p)):
    print("[audio-qa] missing output or cuts.json — skipped"); sys.exit(0)

# decode left channel as f32 (pan, NOT -ac 1: default downmix adds +3 dB and skews levels)
raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", out_mp4, "-vn", "-af", "pan=mono|c0=c0",
     "-f", "f32le", "-"], capture_output=True).stdout
x = array.array("f"); x.frombytes(raw)
n = len(x)
if n < SR:
    print("[audio-qa] output too short — skipped"); sys.exit(0)

segs = json.load(open(cuts_p, encoding="utf-8"))["segments"]
joints, t = [], 0.0
for s in segs[:-1]:
    t += float(s["end"]) - float(s["start"])
    joints.append(t)
expected = t + float(segs[-1]["end"]) - float(segs[-1]["start"])

# ── intentional digital silence next to a joint (2026-09-25) ──
# splice.sh synthesizes exact digital silence (anullsrc) for a segment whose clip has no audio
# stream (screen recordings, b-roll), and some sources carry digital zero themselves (a sync
# beep's gaps, a TTS clip's head/tail). Next to those, every joint scan below misfires: the
# zero-run scan reads the silence as a concat gap ("TIMELINE STRETCH / zero-gaps"), and the
# click scan divides by a ~0 local median ("JOINT CLICKS x97"). Neither is a splice defect, so
# a joint is skipped when either side of it is digital silence: the clip has no audio stream
# (ffprobe), the 150 ms of source touching the joint (the click scan's context reach) holds a
# run of exact zeros >= 1 ms, or the render itself sits below -90 dBFS on one side. Natural
# room tone never gets there, so a normal job skips nothing and reports exactly as before.
# (A mic with a hard noise gate that outputs exact zeros in pauses would also be skipped; the
# click ratio is meaningless against a zero median there too.)
media_dir = os.path.join(job_dir, "raw") if os.path.isdir(os.path.join(job_dir, "raw")) else job_dir

def resolve_clip(clip):
    """Same lookup as splice.sh resolve_clip: exact name, then the same stem with any
    extension (workflows/normalize-source.py may turn X.MOV into X.mov and park the original
    in raw/_source/, which is a directory and so never matches). None when unresolvable."""
    p = clip if os.path.isabs(clip) else os.path.join(media_dir, clip)
    if os.path.exists(p):
        return p
    stem = os.path.splitext(os.path.basename(clip))[0].lower()
    try:
        names = sorted(os.listdir(media_dir))
    except OSError:
        return None
    hits = [f for f in names
            if not f.startswith(".") and ".normalizing." not in f
            and os.path.isfile(os.path.join(media_dir, f))
            and os.path.splitext(f)[0].lower() == stem]
    return os.path.join(media_dir, hits[0]) if len(hits) == 1 else None

_has_audio = {}
def clip_has_audio(path):
    if path not in _has_audio:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                            "stream=index", "-of", "csv=p=0", path], capture_output=True, text=True)
        _has_audio[path] = bool(r.stdout.strip())
    return _has_audio[path]

def source_is_silent(seg, side):
    """True when the source audio touching the joint on this side is digital silence.
    side='tail' = the last 150 ms of the segment, 'head' = its first 150 ms."""
    p = resolve_clip(seg["clip"])
    if p is None:
        return False            # unknown clip: never hide a finding on a guess
    if not clip_has_audio(p):
        return True
    a, b = float(seg["start"]), float(seg["end"])
    ss = max(a, b - 0.15) if side == "tail" else a
    dur = min(0.15, b - a)
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{ss:.6f}", "-t", f"{dur:.6f}", "-i", p, "-vn",
         "-af", "pan=mono|c0=c0", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    y = array.array("f"); y.frombytes(pcm)
    if not y:
        return True             # nothing decodable in the span: silence as far as the mix goes
    run = 0
    for v in y:
        run = run + 1 if v == 0.0 else 0
        if run >= SR // 1000:
            return True
    return False

def side_db(lo, hi):
    """RMS dBFS of the rendered output over [lo, hi) samples (clamped); -inf when empty/zero."""
    s = x[max(0, lo):max(0, min(n, hi))]
    e = sum(v * v for v in s) / max(1, len(s))
    return 10 * math.log10(e) if e > 0 else float("-inf")

def output_is_silent(j):
    """Either side of the joint in the RENDER below -90 dBFS over the click scan's context
    window (20-150 ms from the cut). Catches digital silence the source probe can't see (a
    clip name that no longer resolves); the click ratio against that is meaningless (x303170)."""
    c = int(j * SR)
    return side_db(c - 7200, c - 960) < -90 or side_db(c + 960, c + 7200) < -90

silent_joint = [output_is_silent(joints[i])
                or source_is_silent(segs[i], "tail") or source_is_silent(segs[i + 1], "head")
                for i in range(len(joints))]
n_skip = sum(silent_joint)
skip_note = (f" — skipped {n_skip} joint(s) next to silent/no-audio clips" if n_skip else "")

# ── 0. timeline integrity ──
# decoded length may exceed the EDL sum by up to one AAC frame (1024 samples) of encoder
# tail padding — benign. Anything beyond that, or any internal zero-run at a joint, means
# concat padded silence (the frame-snap regression).
actual = n / SR
slack = (actual - expected) * SR
gaps = []
for j, quiet in zip(joints, silent_joint):
    if quiet:
        continue
    c = int(j * SR)
    run = mx = 0
    for i in range(max(0, c - 2400), min(n, c + 2400)):
        run = run + 1 if x[i] == 0.0 else 0
        mx = max(mx, run)
    if mx >= 48:
        gaps.append((j, mx))
if gaps or slack < -240 or slack > 1100:
    print(f"[audio-qa] ⚠ TIMELINE STRETCH: audio {actual:.3f}s vs EDL sum {expected:.3f}s "
          f"({(actual-expected)*1000:+.0f} ms); zero-gaps at joints: "
          + (", ".join(f"{j:.2f}s ({m} smp)" for j, m in gaps) if gaps else "none")
          + " — check frame-grid snap" + skip_note)
else:
    print(f"[audio-qa] ✓ timeline exact: audio = EDL sum {(actual-expected)*1000:+.1f} ms "
          f"(≤1 AAC frame tail padding), no joint gaps" + skip_note)

# ── 1. joint click scan: max |diff| in ±10 ms vs local median |diff| in ±150 ms ──
bad = []
for j, quiet in zip(joints, silent_joint):
    if quiet:
        continue
    c = int(j * SR)
    if not (SR // 2 < c < n - SR // 2):
        continue
    win = [abs(x[i] - x[i - 1]) for i in range(c - 480, c + 480)]
    ctx = [abs(x[i] - x[i - 1]) for i in range(c - 7200, c - 960)] + \
          [abs(x[i] - x[i - 1]) for i in range(c + 960, c + 7200)]
    med = statistics.median(ctx) or 1e-9
    mx = max(win)
    if mx / med > 40 and mx > 0.01:
        bad.append((j, mx / med))
if bad:
    print(f"[audio-qa] ⚠ JOINT CLICKS at: " +
          ", ".join(f"{j:.2f}s (x{r:.0f})" for j, r in bad) +
          " — crossfades should prevent this; inspect these cuts by ear" + skip_note)
else:
    print(f"[audio-qa] ✓ joints clean ({len(joints) - n_skip} checked){skip_note}")

# ── 1b. ambience continuity: room tone must not dip through a joint ──
# (fading joint edges to silence instead of crossfading punches an audible ~20 ms
#  room-tone hole — measured 8-13 dB dips; this catches that regression)
def rms(seg):
    return math.sqrt(sum(v * v for v in seg) / max(1, len(seg)))
holes = []
for j, quiet in zip(joints, silent_joint):
    if quiet:
        continue            # a cut into digital silence is a deliberate "hole", not a regression
    c = int(j * SR)
    if not (SR // 2 < c < n - SR // 2):
        continue
    at = rms(x[c - 480:c + 720])
    # ref = the quietest natural ambience nearby (10th percentile of 10 ms RMS over ±300 ms)
    # — comparing against adjacent windows flags natural speech decay/onset as a "hole"
    wins = sorted(rms(x[c + k * 480:c + (k + 1) * 480]) for k in range(-30, 30))
    ref = wins[max(0, len(wins) // 10)]
    if ref > 1e-6 and 20 * math.log10(max(at, 1e-9) / ref) < -8:
        holes.append((j, 20 * math.log10(max(at, 1e-9) / ref)))
if holes:
    print(f"[audio-qa] ⚠ AMBIENCE HOLES at: " +
          ", ".join(f"{j:.2f}s ({d:.0f} dB)" for j, d in holes) +
          " — joint audio dips through the cut; crossfade regression")
else:
    print(f"[audio-qa] ✓ ambience continuous through all joints")

# ── 2. limiter pressure: ceiling-pinned density + engagement events ──
CEIL = 0.4995
pinned = [i for i, v in enumerate(x) if abs(v) >= CEIL]
events, last = 0, -10 ** 9
for i in pinned:
    if i - last > SR // 20:
        events += 1
    last = i
pct = 100 * len(pinned) / n
peak = max(abs(v) for v in x)
rms = math.sqrt(sum(v * v for v in x) / n)
print(f"[audio-qa] levels: mean {20*math.log10(rms):.1f} dBFS · peak {20*math.log10(peak):.2f} dBFS"
      f" · limiter pinned {len(pinned)} samples ({pct:.4f}%) in {events} events")
if pct > 0.01 or events > 250:
    print(f"[audio-qa] ⚠ LIMITER PRESSURE high — peaky source at this gain; ducking artifacts likely on"
          f" stressed words. The -17 LUFS target runs the limiter hard on purpose; if it is AUDIBLE, report it: a named AMPLIFY_DB is the creator's call, announced and recorded in RUN.md as a deviation (LANES.md § step 3)")
else:
    print("[audio-qa] ✓ limiter engagement in the transparent range (peaks kissing)")
