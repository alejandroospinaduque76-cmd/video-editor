# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy"]
# ///
"""style-learn.py: MEASURE how a creator edits, from finished videos they like. Onboarding step 3.

  uv run workflows/style-learn.py <video> [<video> ...]              # human summary
  uv run workflows/style-learn.py creator/referencias/ --json        # every video in a folder, JSON
  uv run workflows/style-learn.py <videos> --out creator/perfiles/<slug>/estilo-medido.json

Why (2026-09-28). A buyer cannot describe their editing style in numbers ("¿cuántos cortes por minuto?"), but
their finished videos can. This reads 1–3 edited videos (their own, or a creator whose style they want) and
measures the decisions the pipeline has knobs for:

  pace        cuts per minute, median shot length, zoom punch-ins per minute (scale change across a cut)
  pauses      speech ratio, median / p90 silence KEPT between phrases (what the rough cut should leave)
  audio       integrated loudness, true peak, a music bed under the voice (and how far below it sits)
  captions    burned-in captions or not, their vertical band, letter height, colour, how fast they change
  look        brightness, saturation and contrast of the picture; format, fps, duration

It never decides anything: `workflows/profile.py learn` turns these measurements into profile values, and each
value keeps `source: measured` so the creator can see where it came from and overrule it.
"""
import argparse, json, math, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

import cv2
import numpy as np

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
SR = 16000
HOP = 0.02                  # 20 ms audio frames
SAMPLE_FPS = 4              # frames per second read for picture measures


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None:
        raise SystemExit(f"✗ {path}: no video stream")
    w, h = int(v["width"]), int(v["height"])
    for sd in v.get("side_data_list", []) or []:
        if abs(int(round(float(sd.get("rotation", 0) or 0)))) % 180 == 90:
            w, h = h, w
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 0.0
    return dict(width=w, height=h, fps=round(fps, 3), duration=float(d["format"].get("duration") or 0),
                has_audio=a is not None)


# ── audio ────────────────────────────────────────────────────────────────────────────────────────────────
def audio_frames(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0", "-vn", "-ac", "1",
                          "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    if not raw:
        return None, None
    x = np.frombuffer(raw[: len(raw) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0
    n = int(SR * HOP)
    k = len(x) // n
    fr = x[: k * n].reshape(k, n)
    db = 10 * np.log10((fr ** 2).mean(axis=1) + 1e-12)
    # speech-band share: voice energy sits 150–4000 Hz; music and hiss spread wider
    spec = np.abs(np.fft.rfft(fr * np.hanning(n), axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / SR)
    band = spec[:, (freqs >= 150) & (freqs <= 4000)].sum(axis=1) / (spec.sum(axis=1) + 1e-12)
    return db, band


def loudness(path):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0", "-af", "ebur128=peak=true",
             "-f", "null", "-"]).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def runs(mask):
    """[(start_idx, end_idx_exclusive)] of True runs."""
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            out.append((start, i)); start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def measure_audio(path):
    db, band = audio_frames(path)
    if db is None or len(db) < 50:
        return dict(has_audio=False)
    loud = np.percentile(db, 90)
    # voiced = within 18 dB of the loud level; a 120 ms hang-over bridges consonant gaps inside words
    voiced = db > loud - 18
    hang = int(0.12 / HOP)
    sm = voiced.copy()
    for s, e in runs(~voiced):
        if e - s <= hang and s > 0:
            sm[s:e] = True
    sp = runs(sm)
    sp = [(s, e) for s, e in sp if (e - s) * HOP >= 0.15]
    gaps = [(sp[i][1], sp[i + 1][0]) for i in range(len(sp) - 1)]
    gap_s = np.array([(e - s) * HOP for s, e in gaps]) if gaps else np.array([0.0])
    speech_ratio = float(sm.mean())
    # music bed: in the gaps, is there sound well above the quietest 5% (room tone) that is NOT speech-band?
    floor = np.percentile(db, 5)
    gap_idx = np.concatenate([np.arange(s, e) for s, e in gaps]) if gaps else np.array([], dtype=int)
    music = None
    if len(gap_idx) > 25:
        g_db = db[gap_idx]
        g_band = band[gap_idx]
        bed = float(np.median(g_db))
        music = bool(bed > floor + 12 and np.median(g_band) < 0.85)
        music_db = round(bed - float(np.median(db[sm])), 1)
    i, tp = loudness(path)
    return dict(has_audio=True, speech_ratio=round(speech_ratio, 3),
                pause_median_s=round(float(np.median(gap_s)), 3), pause_p90_s=round(float(np.percentile(gap_s, 90)), 3),
                pauses_per_min=round(len(gaps) / max(1e-6, len(db) * HOP / 60), 1),
                music_bed=music, music_vs_voice_db=music_db if music else None,
                lufs=i, true_peak_db=tp)


# ── picture ──────────────────────────────────────────────────────────────────────────────────────────────
def frames(path, info, width=270):
    h = int(round(info["height"] * width / info["width"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf",
                          f"fps={SAMPLE_FPS},scale={width}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    n = len(raw) // (width * h * 3)
    return np.frombuffer(raw[: n * width * h * 3], dtype=np.uint8).reshape(n, h, width, 3)


def zoom_between(a, b):
    """Scale factor from frame a to frame b (1.0 = same framing), or None when they do not match."""
    orb = cv2.ORB_create(500)
    ka, da = orb.detectAndCompute(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), None)
    kb, db_ = orb.detectAndCompute(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), None)
    if da is None or db_ is None or len(ka) < 20 or len(kb) < 20:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db_)
    if len(m) < 20:
        return None
    pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=4)
    if M is None or inl is None or inl.sum() < 30 or inl.mean() < 0.4:
        return None
    # A punch-in is the SAME picture scaled: once frame a is warped onto b, they must nearly coincide. A cut to a
    # different shot can still yield a RANSAC fit on a few matches (face → laptop on invoice-agent-demo read as a
    # zoom, reviewer ground truth 2026-09-29), but the warped frame then differs as much as the unwarped one.
    h, w = b.shape[:2]
    wa = cv2.warpAffine(a, M, (w, h))
    valid = cv2.warpAffine(np.full(a.shape[:2], 255, np.uint8), M, (w, h)) > 0
    if valid.mean() < 0.5:
        return None
    warped = float(np.abs(wa.astype(np.int16) - b.astype(np.int16))[valid].mean())
    plain = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())
    if warped > 0.5 * plain or warped > 22:
        return None
    return float(math.hypot(M[0, 0], M[1, 0]))


def caption_band(fr, cut_mask):
    """Burned-in captions, found as TEXT that CHANGES while the shot does not.

    Per sampled frame: text-like boxes (strong edges closed horizontally into word/line shapes, 1.2–8% of the frame
    tall, wider than tall). Backgrounds make such boxes too (bookshelves, bricks, windows), but they only change at
    a cut; captions change every fraction of a second inside one shot. So each horizontal band is scored by how
    often it holds text AND how often that text changes between two samples of the same shot. First version
    (colour + band presence) put a bookshelf and a brick wall ahead of the real captions on 2 of 3 references
    (2026-09-28); this one is checked against those three by eye.
    Returns captions, centre y (0..1), line height (share of frame), colour, highlight colour, box/outline, changes/s."""
    n, H, W = fr.shape[:3]
    bins = 50
    per_frame = []                                # [(yc, h, x, y, w) …] per sample
    masks = []
    for f in fr:
        # caption glyphs = bright (white / yellow / saturated highlight) pixels touching very dark ones (the
        # outline, the shadow or the box). A textured background rarely has both side by side; a caption always
        # does. Edge-only detection merged the caption with the countertop behind it (2026-09-28).
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        bright = ((hsv[..., 2] > 215) & ((hsv[..., 1] < 60) | ((hsv[..., 0] >= 18) & (hsv[..., 0] <= 35)))) \
            | ((hsv[..., 1] > 120) & (hsv[..., 2] > 200))
        near_dark = cv2.dilate((hsv[..., 2] < 70).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        # second look: thin light strokes without an outline (the soft, semi-transparent captions of a real-estate
        # tour: montearroyo, yerbabuena, bosque-bogota) — a white top-hat picks strokes thinner than 7 px
        g = hsv[..., 2]
        thin = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 40
        soft = thin & (g > 170) & (hsv[..., 1] < 60)
        m = ((bright & near_dark) | soft).astype(np.uint8)
        closed = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, max(3, W // 20)), np.uint8))
        cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if not (0.012 * H <= h <= 0.09 * H and w >= 0.08 * W):
                continue
            if abs(x + w / 2 - W / 2) > 0.15 * W or m[y:y + h, x:x + w].mean() < 0.05:
                continue
            boxes.append((y + h / 2, h, x, y, w))
        per_frame.append(boxes)
        masks.append(m)
    presence = np.zeros((n, bins), bool)
    for i, boxes in enumerate(per_frame):
        for yc, h, *_ in boxes:
            b = min(bins - 1, int(yc / H * bins))
            presence[i, max(0, b - 1):b + 2] = True
    change = np.zeros(bins)
    same_shot = 0
    for i in range(1, n):
        if cut_mask[i - 1]:
            continue
        same_shot += 1
        for b in range(bins):
            if presence[i, b] or presence[i - 1, b]:
                y0, y1 = int(b / bins * H), int((b + 1) / bins * H)
                if np.mean(masks[i][y0:y1] != masks[i - 1][y0:y1]) > 0.01:
                    change[b] += 1
    if same_shot < 3:
        return dict(captions=False)
    pres_rate = presence.mean(axis=0)
    chg_rate = change / same_shot
    score = pres_rate * chg_rate
    best = int(np.argmax(score))
    changes_per_s = float(chg_rate[best] * SAMPLE_FPS)
    if pres_rate[best] < 0.2 or changes_per_s < 0.4:
        return dict(captions=False)
    y0, y1 = (best - 2) / bins * H, (best + 3) / bins * H
    sel_idx = [(k, bx) for k, boxes in enumerate(per_frame) for bx in boxes if y0 <= bx[0] <= y1]
    yc = float(np.median([bx[0] for _, bx in sel_idx])) / H
    lh = float(np.median([bx[1] for _, bx in sel_idx])) / H
    # colour, highlight and box: only the caption's own glyph pixels (the mask), never the scene behind them —
    # a warm kitchen behind white text read as an "orange highlight" when whole crops were sampled
    hues, white_n, yellow_n, sat_n, tot_n, box_votes = [], 0, 0, 0, 0, []
    for k, (_, h, x, y, w) in sel_idx[:400]:
        f, mk = fr[k], masks[k]
        hsv = cv2.cvtColor(f[y:y + h, x:x + w], cv2.COLOR_BGR2HSV)
        glyph = mk[y:y + h, x:x + w] > 0
        hh, ss, vv = hsv[..., 0][glyph], hsv[..., 1][glyph], hsv[..., 2][glyph]
        tot_n += glyph.sum()
        white_n += int(((ss < 60) & (vv > 170)).sum())
        yl = (hh >= 18) & (hh <= 35) & (ss > 110)
        yellow_n += int(yl.sum())
        sat = (ss > 110) & ~yl
        sat_n += int(sat.sum()); hues += list(hh[sat][:200])
        # a box: the area AROUND the words (half a line above and below) is mostly one flat dark or light colour
        pad = max(1, h // 2)
        ya, yb, xa, xb = max(0, y - pad), min(H, y + h + pad), max(0, x - pad), min(W, x + w + pad)
        ring = cv2.cvtColor(f[ya:yb, xa:xb], cv2.COLOR_BGR2HSV)[..., 2][~(mk[ya:yb, xa:xb] > 0)]
        if ring.size > 30:
            box_votes.append(max((ring < 45).mean(), (ring > 235).mean()) > 0.6)
    main = "yellow" if yellow_n > white_n else "white"
    highlight = None
    if tot_n and main == "white" and yellow_n > 0.05 * tot_n:
        highlight = "yellow"
    elif tot_n and sat_n > 0.05 * tot_n and hues:
        hue = float(np.median(hues)) * 2   # OpenCV hue is 0–180
        highlight = ("red" if hue < 15 or hue >= 345 else "orange" if hue < 45 else "green" if hue < 160
                     else "cyan" if hue < 200 else "blue" if hue < 260 else "magenta")
    boxed = bool(box_votes) and float(np.mean(box_votes)) > 0.5
    return dict(captions=True, caption_center_y=round(yc, 3), caption_line_height=round(lh, 3),
                caption_color=main, caption_highlight=highlight, caption_box=boxed,
                caption_changes_per_s=round(changes_per_s, 2))


CUT_FPS, CUT_W = 15, 96


def detect_cuts(path, info):
    """Edit points, found as an ISOLATED spike in frame-to-frame difference (15 fps, 96 px grey).

    A camera that walks or shakes changes every frame a lot, but steadily; a cut is one frame that changes far more
    than the frames right around it. The first detector (4 fps colour histograms, then a 4x4 grid) counted a walking
    house tour as 45 cuts/min and a handheld presenter as 20 against a truth of 10 (reviewer S1). This one, on the
    reviewer's ground-truth set: jump2 (handheld, cuts 4.0/8.0 s) → 4.0, 8.0; jump (walking tour) → 4.0, 8.0;
    nocut → none; invoice (3.24/7.71) → 3.27, 7.73; arena-hdr (one cut on a filmed monitor, same framing) → missed.
    It errs toward missing a near-invisible cut, never toward inventing pace."""
    h = int(round(info["height"] * CUT_W / info["width"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf",
                          f"fps={CUT_FPS},scale={CUT_W}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (CUT_W * h)
    if n < 10:
        return []
    g = np.frombuffer(raw[: n * CUT_W * h], np.uint8).reshape(n, h, CUT_W).astype(np.int16)
    d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))
    out = []
    for i in range(len(d)):
        nb = np.concatenate([d[max(0, i - 7):max(0, i - 1)], d[i + 2:i + 8]])
        if len(nb) < 4:
            continue
        neigh = max(d[i - 1] if i else 0.0, d[i + 1] if i + 1 < len(d) else 0.0)
        if d[i] >= max(6.0, 1.6 * float(np.median(nb))) and d[i] >= 1.7 * neigh:
            out.append((i + 1) / CUT_FPS)
    return out


def measure_picture(path, info):
    fr = frames(path, info)
    if len(fr) < 4:
        return {}
    cut_times = detect_cuts(path, info)
    cut_idx = sorted({min(len(fr) - 1, max(1, int(math.ceil(t * SAMPLE_FPS)))) for t in cut_times})
    # punch-ins: across a cut, the same scene reframed ≥ 8% larger or smaller
    zooms = []
    for i in cut_idx:
        z = zoom_between(fr[i - 1], fr[i])
        if z is not None and abs(z - 1) >= 0.08 and 0.6 < z < 1.8:
            zooms.append(round(z, 2))
    minutes = max(1e-6, info["duration"] / 60)
    shots = np.diff([0.0] + list(cut_times) + [info["duration"]])
    hsv = np.array([cv2.cvtColor(f, cv2.COLOR_BGR2HSV).reshape(-1, 3).mean(axis=0) for f in fr[:: max(1, len(fr) // 40)]])
    gray = np.array([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).std() for f in fr[:: max(1, len(fr) // 40)]])
    out = dict(cuts_per_min=round(len(cut_times) / minutes, 1), median_shot_s=round(float(np.median(shots)), 2),
               cut_times=[round(t, 2) for t in cut_times[:200]],
               punch_ins_per_min=round(len(zooms) / minutes, 1), punch_in_scales=sorted(set(zooms))[:8],
               brightness=round(float(hsv[:, 2].mean() / 255), 3), saturation=round(float(hsv[:, 1].mean() / 255), 3),
               contrast=round(float(gray.mean() / 128), 3))
    cut_mask = np.zeros(len(fr) - 1, bool)
    for i in cut_idx:
        cut_mask[i - 1] = True
    # captions change inside a shot; a camera move also changes the band, so treat frames around each cut as
    # "not the same shot" (±1 sample)
    for i in cut_idx:
        cut_mask[max(0, i - 2):min(len(cut_mask), i + 1)] = True
    out.update(caption_band(fr, cut_mask))
    return out


WORDS_PY = r"""
import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("large-v3", device="cpu", compute_type="int8")
out = []
for wav in sys.argv[1:]:   # one model load for every reference: loading large-v3 is most of the time
    segs, info = m.transcribe(wav, word_timestamps=True, vad_filter=True, beam_size=1)
    ws = [dict(w=w.word.strip(), s=round(w.start, 3), e=round(w.end, 3)) for sg in segs for w in (sg.words or [])]
    out.append(dict(language=info.language, words=ws))
print(json.dumps(out))
"""
ALWAYS_FILLERS = {"eh", "ehh", "em", "emm", "mmm", "mm", "um", "uh", "uhm"}
MARKERS = {"este", "bueno", "pues", "tipo", "digamos", "like"}   # only when isolated by pauses (reviewer S2)


def whisper_python():
    import os
    venv = Path(os.environ.get("VIDEO_EDITOR_WHISPERX_VENV") or Path.home() / ".cache/video-editor/whisperx-venv")
    for py in (venv / "bin/python", venv / "Scripts/python.exe"):
        if py.is_file():
            return py
    return None


def start_words(paths, td, max_s=60):
    """Start the word-timestamp pass in the BACKGROUND (it is most of the wall-clock: a large-v3 load plus decoding)
    so the picture pass runs at the same time. Returns a handle for finish_words, or None when unavailable.
    Skipped while `transcribe.sh --prefetch` is still downloading the model (two downloads of one model collide);
    the empezar skill re-runs the measurement after the first edit in that case."""
    import os
    py = whisper_python()
    work = Path(os.environ.get("VIDEO_EDITOR_WORK") or "/tmp/video-editor")
    pidf = work / "_prefetch" / "prefetch.pid"
    if pidf.exists():
        try:
            os.kill(int(pidf.read_text().strip()), 0)   # a live prefetch is downloading the model right now
            return None
        except (ValueError, OSError):
            pass                                        # stale pid file from a finished/killed prefetch
    if not py or not paths:
        return None
    wavs = []
    for k, path in enumerate(paths):
        wav = Path(td) / f"a{k}.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-t", str(max_s), "-i", str(path), "-map", "0:a:0",
                        "-ac", "1", "-ar", "16000", str(wav)], check=False)
        wavs.append(str(wav))
    env = dict(os.environ)
    import platform
    if platform.system() == "Darwin" and platform.machine() == "x86_64":
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"   # Intel Mac stack: two OpenMP runtimes (see transcribe.sh)
    return subprocess.Popen([str(py), "-c", WORDS_PY, *wavs], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, env=env)


def finish_words(proc, n):
    if proc is None:
        return [{} for _ in range(n)]
    out, _ = proc.communicate()
    try:
        data = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return [{} for _ in range(n)]
    return [_word_stats(d) for d in data]


def _word_stats(d):
    ws = d["words"]
    if len(ws) < 10:
        return dict(language=d.get("language"))
    span = ws[-1]["e"] - ws[0]["s"]
    gaps = np.array([b["s"] - a["e"] for a, b in zip(ws, ws[1:])])
    pauses = gaps[gaps > 0.12]
    norm = [re.sub(r"[^\wáéíóúñü]", "", w["w"].lower()) for w in ws]
    fill = 0
    for k, n in enumerate(norm):
        before = ws[k]["s"] - ws[k - 1]["e"] if k else 9
        after = ws[k + 1]["s"] - ws[k]["e"] if k + 1 < len(ws) else 9
        if n in ALWAYS_FILLERS:
            fill += 1
        elif n in MARKERS and after >= 0.25 and (before >= 0.25 or ws[k]["w"].rstrip().endswith((",", "…", "..."))):
            fill += 1
        elif n == "o" and k + 1 < len(norm) and norm[k + 1] == "sea":
            fill += 1
    return dict(language=d.get("language"), words_per_s=round(len(ws) / max(1e-6, span), 2),
                pause_median_s=round(float(np.median(pauses)), 3) if len(pauses) else 0.0,
                pause_p90_s=round(float(np.percentile(pauses, 90)), 3) if len(pauses) else 0.0,
                pauses_per_min=round(len(pauses) / max(1e-6, span / 60), 1),
                filler_words_per_min=round(fill / max(1e-6, span / 60), 1),
                pause_source="words")


def measure(path):
    info = probe(path)
    res = dict(file=Path(path).name, format="vertical" if info["height"] > info["width"] else "horizontal",
               width=info["width"], height=info["height"], fps=info["fps"], duration_s=round(info["duration"], 2))
    if info["has_audio"]:
        res.update(measure_audio(path))
    res.update(measure_picture(path, info))
    return res


def summary(results):
    """Duration-weighted average of the numeric measures across references."""
    w = np.array([r["duration_s"] for r in results], dtype=float)
    keys = [k for k in results[0] if isinstance(results[0][k], (int, float)) and not isinstance(results[0][k], bool)]
    agg = {}
    for k in keys:
        vals = [(r.get(k), wi) for r, wi in zip(results, w) if isinstance(r.get(k), (int, float))]
        if vals:
            agg[k] = round(sum(v * wi for v, wi in vals) / sum(wi for _, wi in vals), 3)
    for k in ("captions", "music_bed", "caption_box"):
        vs = [r.get(k) for r in results if r.get(k) is not None]
        if vs:
            agg[k] = sum(vs) >= len(vs) / 2
    fmts = [r["format"] for r in results]
    agg["format"] = max(set(fmts), key=fmts.count)
    for k in ("caption_color", "language", "pause_source"):
        vals = [r.get(k) for r in results if r.get(k)]
        if vals:
            agg[k] = max(set(vals), key=vals.count)
    # highlight: a reference WITH captions but without a highlight is a vote for "none" (c3, 2026-09-29: one cyan
    # reel out of two was enough to give the buyer a cyan highlight)
    votes = [r.get("caption_highlight") or "none" for r in results if r.get("captions")]
    if votes:
        best = max(set(votes), key=votes.count)
        if best != "none" and votes.count(best) > len(votes) / 2:
            agg["caption_highlight"] = best
    return agg


def human(r):
    lines = [f"{r['file']}: {r['format']} {r['width']}x{r['height']} · {r['duration_s']:.0f} s"]
    if "cuts_per_min" in r:
        lines.append(f"  ritmo: al menos {r['cuts_per_min']} cortes/min · toma mediana {r['median_shot_s']} s · "
                     f"{r['punch_ins_per_min']} zooms/min")
    if r.get("has_audio"):
        lines.append(f"  pausas: mediana {r['pause_median_s']} s · p90 {r['pause_p90_s']} s"
                     + (f" · {r['words_per_s']} palabras/s · {r['filler_words_per_min']} muletillas/min" if r.get("words_per_s")
                        else f" · voz {r['speech_ratio']*100:.0f}% del tiempo (sin transcripción)"))
        lines.append(f"  audio: {r['lufs']} LUFS · pico {r['true_peak_db']} dB · música de fondo: "
                     + ("sí, " + str(r['music_vs_voice_db']) + " dB bajo la voz" if r.get("music_bed") else "no"))
    if "captions" in r:
        lines.append("  subtítulos: " + (f"sí, {r['caption_color']}, a {r['caption_center_y']*100:.0f}% de alto, letra "
                                         f"{r['caption_line_height']*100:.1f}% del cuadro, {'en caja' if r['caption_box'] else 'con borde'}"
                                         f"{', resaltado ' + r['caption_highlight'] if r.get('caption_highlight') else ''}, {r['caption_changes_per_s']} cambios/s"
                                         if r["captions"] else "no detectados"))
    if "brightness" in r:
        lines.append(f"  imagen: brillo {r['brightness']} · saturación {r['saturation']} · contraste {r['contrast']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--no-words", action="store_true", help="skip the word-timestamp pass (no transcription engine yet)")
    a = ap.parse_args()
    files = []
    for x in a.inputs:
        p = Path(x)
        files += sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT) if p.is_dir() else [p]
    if not files:
        raise SystemExit("✗ no videos: put 1–3 finished videos in creator/referencias/")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with_audio = [f for f in files if probe(f)["has_audio"]]
        proc = None if a.no_words else start_words(with_audio, td)
        results = [measure(f) for f in files]
        by_name = dict(zip([f.name for f in with_audio], finish_words(proc, len(with_audio))))
    for r in results:
        r.update(by_name.get(r["file"], {}))   # word-based pauses override the energy-based ones when available
    data = dict(version=1, references=results, summary=summary(results))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(data, indent=1, ensure_ascii=False))
    if a.json:
        print(json.dumps(data, indent=1, ensure_ascii=False))
    else:
        for r in results:
            print(human(r))
        if a.out:
            print(f"→ {a.out}")


if __name__ == "__main__":
    main()
