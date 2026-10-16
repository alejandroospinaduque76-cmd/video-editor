#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy"]
# ///
"""face-guard.py — THE FACE LAW for short-form (9:16): nothing covers the face, ever, and it is MEASURED.

The user's key rule (2026-09-14, after a chip landed on his eyes): captions, chips, tiles, icons,
textures and lines never touch the face. Fixed y-numbers cannot promise that — a WhatsApp clip scaled
to 1080x1920 puts the eyes at y~1000 — so the face is detected on the FOOTAGE (OpenCV YuNet, the model
vendored in assets/models/) and everything is judged against a KEEP-OUT box: the union of every face
box in the window plus margins (hair above, cheeks/ears to the sides, the jaw below).

Two modes:

  zones  — BEFORE authoring: the keep-out and the free zones for a beat, in sequence coordinates.
    uv run workflows/face-guard.py zones <video> --from 3.7 --to 6.0 [--seq 1080x1920] [--zoom 1.09] [--json] [--annotate out.png]
    A raw clip that is not the sequence size (720x1280 → 1080x1920) is mapped by WIDTH, centred vertically —
    the way the lane conforms a phone clip (Motion 150 % on example-reel). A clip the lane fits differently
    (a landscape clip cropped to fill the height) is not covered: measure that beat on a program frame.
    --zoom widens the keep-out for a beat that carries a baked punch-in (Transform 100→109 grows the face).

  check  — AFTER placement: the gate. Every placed overlay render (placement.json rows overlay / text /
    captions / headline; full-screens exempt but must be opaque) is swept frame by frame on its alpha
    plane, and any ink inside the keep-out of ITS OWN timeline moment fails. Rows are split at the V1 cut
    boundaries (cuts.json), so a caption layer spanning the reel is judged segment by segment against that
    segment's face. A detection miss never shrinks the keep-out (union, not median). Ink that a person
    cut-out on the track above covers is subtracted first (placement rows of kind "cutout", or plan cells of
    kind bed-behind / type-behind). The same sweep fails solid ink in the platform bands (y < 200, y > 1620).
    uv run workflows/face-guard.py check projects/<job> [--ids g1,g2] [--seq WxH] [--json hf-graphics/face-report.json]
    The sequence is read off the base cut (outputs/<job>.mp4, else the first segment's raw clip) unless --seq is
    given: a vertical base is the 1080x1920 short-form frame whatever its pixel size, a horizontal one is its own
    size. On a 16:9 sequence only the face is judged (no Instagram zone, graphics-qa.py owns the 16:9 bands) and
    a render of the same aspect at another size (1080p over 4K footage) is measured scaled.
    Waiver: hf-graphics/qa-waivers.json {"g7": {"face": "the annotation circles his glasses by design"}}
    Exit 1 on any FAIL.

  --selftest — proves the mapping, the union, the sweep and the tolerance on synthetic renders, offline.

graphics-qa.py refuses 9:16 renders by design (its geometry is 16:9), so on a short-form job THIS is
the step-5 gate for the face; graphics-build runs it before edit-review.
"""
import argparse, glob, json, math, os, subprocess, sys, tempfile
import numpy as np

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(REPO, "assets", "models", "face_detection_yunet_2023mar.onnx")
MARGIN_TOP, MARGIN_SIDE, MARGIN_BOTTOM = 140, 70, 50   # hair · cheeks/ears · under the jaw (px, sequence frame)
STEP = 0.25            # detection sample interval, seconds (samples sit on a global grid so rows share the cache)
MIN_FACE = 0.05        # a face shorter than this share of the clip height is not the speaker: a thumbnail inside a
                       # screen recording (example-reel g4: the YouTube promo avatar, ~4 %) must not open a keep-out, while a
                       # presenter in a wide shot (a house tour, ~6-8 %) still must. --min-face overrides per job.
UNDER_CUTOUT = ('bed-behind', 'type-behind')   # plan kinds whose ink is BEHIND the person cut-out on the track above
PUSH_IN_ZOOM = 1.09    # the baked punch-in (bridge `zoom` 100→109) grows the face by this much about the frame centre
SAFE_TOP, SAFE_BOTTOM = 200, 1620   # the short-form safe bands (CLAUDE.md)
# THE INSTAGRAM SAFE ZONE (the user's unbreakable rule, 2026-09-28, reference-craft.md § 0b): on a tall iPhone IG fills
# the height and crops the reel's sides, and its buttons sit on the right. Key ink outside this rectangle, or in the
# button column, is a FAIL (waive a prop passing through with {"gN": {"zone": "..."}}).
IG_X0, IG_X1, IG_Y0, IG_Y1 = 180, 905, 200, 1507
IG_COL_X, IG_COL_Y = 845, 826          # the like / comment / share column: x > 845 for y > 826
REFRAME = [1.0, 0.0]                   # the V1 reframe (Motion scale factor over the width-fit, vertical offset px): plan "reframe"
PUSH_PIVOT_Y = None                    # punch-ins pivot on the eyes when set (plan "push_in_pivot_y"), else on the frame centre
ALPHA_INK = 40         # an alpha above this is ink (a 0.35-opacity texture line is ~90: it counts)
ALPHA_SOLID = 160      # the platform-band check only cares about solid ink (a feathered texture tail may cross it)
TOLERANCE = 0.003      # ink inside the keep-out, as a share of its area, that is anti-aliasing noise, not a defect
CUTOUT_COVER = 0.85    # a cut-out silhouette covering at least this share of the nearest detected face box protects the face for that frame
SWEEP_DIV = 4          # the alpha plane is swept at 1/4 scale (270x480 for 1080x1920)


def probe(video):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", video],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    w, h = int(j["width"]), int(j["height"])
    rot = 0
    for sd in j.get("side_data_list", []):
        if "rotation" in sd: rot = int(sd["rotation"])
    if abs(rot) == 90: w, h = h, w                       # ffmpeg autorotates on decode; the upright size is what we see
    num, den = j["r_frame_rate"].split("/")
    dur = float(j.get("duration") or 0) or float(json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video], capture_output=True, text=True).stdout)["format"]["duration"])
    return {"w": w, "h": h, "fps": int(num) / int(den), "dur": dur, "pix": j.get("pix_fmt", "")}


class Detector:
    """YuNet, one instance per frame size, largest face per frame, cached per (clip, t). Samples sit on a
    global STEP grid in CLIP time, so `faces(video, times)` decodes a whole run of samples in ONE ffmpeg
    pass (`fps=1/STEP` from the first missing sample) instead of one seek per sample: a 35 s caption row
    went from ~2 min to seconds, and rows sharing footage share the cache."""
    def __init__(self, min_face=MIN_FACE):
        import cv2
        self.cv2 = cv2; self.dets = {}; self.cache = {}; self.tmp = tempfile.mkdtemp(); self.min_face = min_face

    def _detect(self, img):
        h, w = img.shape[:2]
        if (w, h) not in self.dets:
            self.dets[(w, h)] = self.cv2.FaceDetectorYN.create(MODEL, "", (w, h), 0.6, 0.3, 5000)
        _, faces = self.dets[(w, h)].detect(img)
        if faces is not None and len(faces):
            # Largest among the CONFIDENT boxes only: a hand holding a mic scored 0.62 next to a 0.91 face and, being
            # larger, won "largest" and stretched the keep-out to y1785 (your-brand-3, 2026-09-25). A second real face
            # (a guest, an avatar) scores near the best one, so it stays a candidate.
            best = max(float(d[14]) for d in faces)
            faces = [d for d in faces if float(d[14]) >= best - 0.15]
            x, y, bw, bh = max(((d[0], d[1], d[2], d[3]) for d in faces), key=lambda d: d[2] * d[3])
            if bh >= self.min_face * h:                     # the speaker, not an avatar on a screen
                return (float(x), float(y), float(bw), float(bh), w, h)
        return None

    def faces(self, video, times):
        """Face boxes for a list of clip times (multiples of STEP): one decode pass for the missing ones."""
        missing = [t for t in times if (video, round(t, 2)) not in self.cache]
        if missing:
            t0, t1 = min(missing), max(missing)
            d = tempfile.mkdtemp(dir=self.tmp)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t0):.3f}", "-t", f"{t1 - t0 + STEP / 2:.3f}", "-i", video,
                            "-vf", f"fps={1 / STEP}", os.path.join(d, "%05d.png")], check=False)
            for k, fn in enumerate(sorted(os.listdir(d))):
                t = round(t0 + k * STEP, 2)
                img = self.cv2.imread(os.path.join(d, fn))
                self.cache[(video, t)] = self._detect(img) if img is not None else None
                os.remove(os.path.join(d, fn))
            for t in missing: self.cache.setdefault((video, round(t, 2)), None)   # past the clip end: no face
        return [self.cache[(video, round(t, 2))] for t in times]

    def face(self, video, t):
        return self.faces(video, [t])[0]


def to_seq(box, seq_w, seq_h):
    """A face box in clip pixels → sequence pixels: the clip fills the sequence WIDTH and is centred vertically
    (a 720x1280 clip at 150 % in a 1080x1920 sequence; a 1080x1920 clip maps 1:1)."""
    x, y, bw, bh, w, h = box
    s = seq_w / w
    oy = (seq_h - h * s) / 2
    k, dy = REFRAME                    # a reframed V1 (the eyes lifted to the upper third): scale about the frame centre, then shift
    cx, cy = seq_w / 2, seq_h / 2
    return (cx + (x * s - cx) * k, cy + (y * s + oy - cy) * k + dy, bw * s * k, bh * s * k)


def grid(lo, hi, step=STEP):
    """Sample times on a global grid inside [lo, hi] (at least one), so rows sharing footage share detections."""
    ts = [k * step for k in range(math.ceil(lo / step), math.floor(hi / step) + 1) if lo <= k * step <= hi]
    return ts or [lo + min(0.02, max(0.0, (hi - lo) / 2))]


def keepout(boxes, seq_w, seq_h, zoom=1.0, margins=True):
    """Union of the face boxes plus margins, grown about the frame centre by `zoom`, clamped; None when no face.
    margins=False gives the bare union (the detector's own box): what a frame is judged against once a person
    cut-out is subtracted, because the silhouette then IS the boundary and a bed showing beside the hair is the design."""
    if not boxes: return None
    ms, mt, mb = (MARGIN_SIDE, MARGIN_TOP, MARGIN_BOTTOM) if margins else (0, 0, 0)
    l = min(b[0] for b in boxes) - ms
    t = min(b[1] for b in boxes) - mt
    r = max(b[0] + b[2] for b in boxes) + ms
    b_ = max(b[1] + b[3] for b in boxes) + mb
    if zoom != 1.0:
        cx, cy = seq_w / 2, (PUSH_PIVOT_Y if PUSH_PIVOT_Y is not None else seq_h / 2)   # eyeline punch-ins pivot on the eyes
        l, r = cx + (l - cx) * zoom, cx + (r - cx) * zoom
        t, b_ = cy + (t - cy) * zoom, cy + (b_ - cy) * zoom
    return [int(max(0, l)), int(max(0, t)), int(min(seq_w, r)), int(min(seq_h, b_))]


def zones_for(ko, seq_w, seq_h):
    """The free rectangles around a keep-out, inside the INSTAGRAM safe zone (x 180→905 · y 200→1507, the right-hand
    button column x > 845 below y 826 excluded — reference-craft.md § 0b): above · below · left · right."""
    if ko is None:
        return {"above": [IG_X0, IG_Y0, IG_X1, IG_Y1], "below": None, "left": None, "right": None}
    l, t, r, b = ko
    z = {}
    z["above"] = [IG_X0, IG_Y0, IG_X1, t] if t - IG_Y0 >= 120 else None
    z["below"] = [IG_X0, b, IG_COL_X if b >= IG_COL_Y else IG_X1, IG_Y1] if IG_Y1 - b >= 120 else None
    z["left"] = [IG_X0, max(IG_Y0, t), l, min(IG_Y1, b)] if l - IG_X0 >= 260 else None
    rx1 = IG_COL_X if min(IG_Y1, b) > IG_COL_Y else IG_X1
    z["right"] = [r, max(IG_Y0, t), rx1, min(IG_Y1, b)] if rx1 - r >= 260 else None
    return z


def fmt_zone(name, z):
    if not z: return f"  {name:6s} —"
    x0, y0, x1, y1 = z
    return f"  {name:6s} x {x0:4d}→{x1:4d} · y {y0:4d}→{y1:4d}   ({x1 - x0}×{y1 - y0})"


# ── zones ────────────────────────────────────────────────────────────────────
def cmd_zones(a):
    global PUSH_PIVOT_Y
    seq_w, seq_h = map(int, a.seq.lower().split("x"))
    if a.reframe: REFRAME[0], REFRAME[1] = map(float, a.reframe.split(","))
    if a.pivot is not None: PUSH_PIVOT_Y = a.pivot
    pr = probe(a.video)
    t1 = a.t1 if a.t1 is not None else pr["dur"]
    det = Detector(a.min_face)
    boxes, misses = [], 0
    for bx in det.faces(a.video, grid(a.t0, t1, a.step)):
        if bx: boxes.append(to_seq(bx, seq_w, seq_h))
        else: misses += 1
    ko = keepout(boxes, seq_w, seq_h, a.zoom)
    z = zones_for(ko, seq_w, seq_h)
    out = {"video": a.video, "from": a.t0, "to": t1, "clip": [pr["w"], pr["h"]], "seq": [seq_w, seq_h], "zoom": a.zoom,
           "samples": len(boxes), "misses": misses, "keepout": ko, "zones": z,
           "margins": {"top": MARGIN_TOP, "side": MARGIN_SIDE, "bottom": MARGIN_BOTTOM}}
    if a.annotate:
        import cv2
        f = os.path.join(det.tmp, "a.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(a.t0 + t1) / 2:.3f}", "-i", a.video, "-frames:v", "1",
                        "-vf", f"scale={seq_w}:-2,pad={seq_w}:{seq_h}:0:(oh-ih)/2", f], check=True)
        img = cv2.imread(f)
        if ko: cv2.rectangle(img, (ko[0], ko[1]), (ko[2], ko[3]), (0, 0, 255), 5)
        for name, zz in z.items():
            if zz: cv2.rectangle(img, (zz[0] + 3, zz[1] + 3), (zz[2] - 3, zz[3] - 3), (0, 255, 0), 3); cv2.putText(img, name, (zz[0] + 14, zz[1] + 44), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.imwrite(a.annotate, img); out["annotate"] = a.annotate
    if a.json:
        print(json.dumps(out, indent=2)); return
    print(f"{os.path.basename(a.video)}  {pr['w']}x{pr['h']} → seq {seq_w}x{seq_h}   window {a.t0:.2f}→{t1:.2f}s   faces {len(boxes)} (+{misses} no-face)" + (f"   zoom {a.zoom}" if a.zoom != 1.0 else ""))
    if ko is None:
        print("no face in this window: the whole safe frame is free (y 200 → 1620)"); return
    print(f"KEEP-OUT (face + hair {MARGIN_TOP} / sides {MARGIN_SIDE} / jaw {MARGIN_BOTTOM}):  x {ko[0]}→{ko[2]} · y {ko[1]}→{ko[3]}")
    print("free zones (inside the safe bands):")
    for k in ("above", "below", "left", "right"): print(fmt_zone(k, z[k]))
    if a.annotate: print(f"  annotated: {a.annotate}")


# ── check ────────────────────────────────────────────────────────────────────
def frames_alpha(path, w, h, max_frames=None):
    """Yield the alpha plane of every frame, downscaled, as uint8 arrays (at most max_frames)."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"alphaextract,scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)   # stderr: the pipe is closed early on purpose
    n = w * h; i = 0
    while max_frames is None or i < max_frames:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        yield np.frombuffer(buf, np.uint8).reshape(h, w); i += 1
    p.stdout.close(); p.wait()


def sweep(f, start, end, F, kos, seq_w, seq_h, cutout_alpha=None):
    """Sweep one render's alpha plane. kos = [(lo, hi, keepout[, bare_keepout])] in timeline seconds; cutout_alpha(t) → the
    cut-out's alpha at the sweep scale (or None). A frame a cut-out covers is judged against the BARE face box (the
    silhouette is the boundary there). Returns (worst_share, worst_frame, its keep-out, band_hits)."""
    sw, sh = seq_w // SWEEP_DIV, seq_h // SWEEP_DIV
    # the danger mask: outside the IG safe rectangle, or in the right-hand button column (reference-craft.md § 0b)
    danger = np.ones((sh, sw), bool)
    danger[IG_Y0 // SWEEP_DIV:IG_Y1 // SWEEP_DIV, IG_X0 // SWEEP_DIV:IG_X1 // SWEEP_DIV] = False
    danger[IG_COL_Y // SWEEP_DIV:, IG_COL_X // SWEEP_DIV:] = True
    if seq_w >= seq_h:
        # 2026-09-29: the IG rectangle is a 9:16 number; on a 16:9 YouTube frame it flagged 5 correct cards
        # (chat-only long-form QA). A horizontal sequence has no platform bands: graphics-qa.py's band/edge sweep
        # owns them, so here only the face is judged.
        danger[:] = False
    worst = (0.0, -1, None); band = None
    n_max = int(round((end - start) / F)) + 1          # never judge frames past the placed window (a caption mov may be longer)
    for i, al in enumerate(frames_alpha(f, sw, sh, n_max)):
        t = start + i * F
        covered = False
        if cutout_alpha is not None:
            co = cutout_alpha(t)
            if co is not None: al = np.where(co > 127, 0, al); covered = True   # what the person covers is not on screen
        if band is None:
            hit = (al > ALPHA_SOLID) & danger
            if hit.any():
                ys, xs = np.nonzero(hit)
                band = (i, f"IG danger zone at x {int(xs.min()) * SWEEP_DIV}→{int(xs.max() + 1) * SWEEP_DIV} y {int(ys.min()) * SWEEP_DIV}→{int(ys.max() + 1) * SWEEP_DIV}")
        seg = next((k for k in kos if k[0] - 0.5 * F <= t <= k[1] + 0.5 * F), None)
        if seg is None: continue
        ko = seg[2]
        if covered and len(seg) > 4 and seg[4]:
            # a person cut-out covers this frame: the SILHOUETTE is the boundary. If it covers the face detected
            # NEAREST IN TIME to this frame (one tight box, not the segment's union — the head moves), the mask did
            # not fail, the face is protected by construction and ink beside the head is the design (a bed behind
            # him). If the mask failed, judge the frame like any other.
            ts, box = min(seg[4], key=lambda sb: abs(sb[0] - t))
            bl, bt, br, bb = [v // SWEEP_DIV for v in box]
            face = co[bt:bb, bl:br]
            if face.size and float((face > 127).mean()) >= CUTOUT_COVER:
                if worst[2] is None: worst = (0.0, i, seg[3])
                continue
        if ko is None: continue
        l, tp, rr, b = [v // SWEEP_DIV for v in ko]
        region = al[tp:b, l:rr]
        if region.size == 0: continue
        share = float((region > ALPHA_INK).sum()) / region.size
        if share > worst[0] or worst[2] is None: worst = (share, i, ko)   # a 0 % frame still records that a face WAS there
    return worst[0], worst[1], worst[2], band


class CutoutAlpha:
    """Alpha frames of the person cut-out rows (placement kind "cutout"), decoded once at the sweep scale."""
    def __init__(self, rows, seq_w, seq_h):
        self.rows = []
        sw, sh = seq_w // SWEEP_DIV, seq_h // SWEEP_DIV
        for r in rows:
            if not os.path.exists(r["file"]): continue
            pr = probe(r["file"])
            self.rows.append((r["start"], r["end"], 1.0 / pr["fps"], list(frames_alpha(r["file"], sw, sh))))

    def __call__(self, t):
        for s, e, F, fr in self.rows:
            if s - 0.5 * F <= t <= e + 0.5 * F:
                i = int(round((t - s) / F))
                if 0 <= i < len(fr): return fr[i]
        return None


def base_frame(job, segs):
    """The sequence `check` judges in when --seq is not given (2026-09-29): the base cut the overlays sit on.
    edit-review runs `check` on every job and the old fixed 1080x1920 default failed every card of a 16:9 job
    ("render is 1920x1080, the sequence is 1080x1920" → FACE LAW BROKEN). outputs/<job>.mp4 first; an app lane
    (RENDER=0) has no flat cut, so then the raw clip of the first segment. A VERTICAL base is the 1080x1920
    short-form frame whatever its pixels (a 720x1280 or 2160x3840 phone clip is conformed to it: the renders, the
    IG zone and the margins are all 1080x1920 numbers); a horizontal base is its own size."""
    name = os.path.basename(job)
    for c in [os.path.join(job, "outputs", f"{name}.mp4")] + [s["clip"] for s in segs[:1] if s["clip"]]:
        if os.path.isfile(c):
            pr = probe(c)
            return (1080, 1920, c) if pr["h"] > pr["w"] else (pr["w"], pr["h"], c)
    return 1080, 1920, None


def row_file(job, f):
    """A placement row's file: absolute as written; a relative one is looked up in the job folder, its hf-graphics/,
    then the kit root (the folder every tool runs from). assemble.py, graphics-qa.py and face-guard.py all read a row
    this way (c3, v1.4 QA 2026-09-29: assemble resolved it from the job, the two gates from the kit root)."""
    if os.path.isabs(f):
        return f
    kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for c in (os.path.join(job, f), os.path.join(job, "hf-graphics", f), os.path.join(kit, f), os.path.abspath(f)):
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(job, f)


def cmd_check(a):
    job = os.path.abspath(a.job); hf = os.path.join(job, "hf-graphics")
    pj = os.path.join(hf, "placement.json")
    if os.path.exists(pj):
        rows = json.load(open(pj))
    else:
        # a captions-only chat-only job may never have written placement.json (2026-09-25 buyer test):
        # check the caption layer on its own instead of dying on a raw FileNotFoundError
        cap = os.path.join(hf, "captions", "renders", "captions-alpha.mov")
        if not os.path.exists(cap):
            sys.exit(f"no {pj} and no {cap}: nothing placed to check. Write placement.json "
                     "(one row per placed graphic, see lanes/chat-only/incremental-graphics.md) and re-run.")
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", cap],
                                   capture_output=True, text=True).stdout.strip() or 0)
        rows = [{"id": "captions", "kind": "captions", "file": cap, "start": 0.0, "end": dur, "track": "top"}]
        print(f"· no placement.json — checking the caption layer alone ({dur:.2f}s)")
    for r in rows:
        if r.get("file"): r["file"] = row_file(job, r["file"])
        # ids as TEXT (2026-09-29): the plan schema writes ints ("id": 1) while --ids, the waiver keys and `cells`
        # below are strings, so an int id silently lost its waiver, its push-in and its --ids filter
        r["id"] = str(r["id"])
    cut_rows = [r for r in rows if r.get("kind") == "cutout"]
    if a.ids: rows = [r for r in rows if r["id"] in a.ids.split(",")]
    waivers = {}
    wp = os.path.join(hf, "qa-waivers.json")
    if os.path.exists(wp): waivers = json.load(open(wp))
    # timeline → raw: cuts.json segments in order; without an EDL, the flat cut is the footage
    segs = []
    cp = os.path.join(job, "transcript", "cuts.json")
    if os.path.exists(cp):
        t = 0.0
        for s in json.load(open(cp))["segments"]:
            clip = s["clip"]
            cand = [clip, os.path.join(job, "raw", clip)] + sorted(glob.glob(os.path.join(job, "raw", os.path.splitext(clip)[0] + ".*")))
            path = next((c for c in cand if os.path.isfile(c)), None)
            d = float(s["end"]) - float(s["start"])
            segs.append({"t0": t, "t1": t + d, "clip": path, "in": float(s["start"])}); t += d
    else:
        base = sorted(glob.glob(os.path.join(job, "outputs", "*.mp4")))
        if not base: sys.exit("no transcript/cuts.json and no outputs/*.mp4: nothing to measure the face on")
        segs.append({"t0": 0.0, "t1": probe(base[0])["dur"], "clip": base[0], "in": 0.0})
    if a.seq:                                   # an explicit --seq always wins
        seq_w, seq_h = map(int, a.seq.lower().split("x"))
    else:
        seq_w, seq_h, seq_src = base_frame(job, segs)
        print(f"· sequence {seq_w}x{seq_h} from {os.path.relpath(seq_src, job) if seq_src else 'the short-form default (no base cut, no raw clip)'}"
              + ("" if seq_h > seq_w else ": horizontal, the face only (no Instagram zone)") + "  (--seq WxH overrides)")
    det = Detector(a.min_face)
    cells, beats = {}, []
    pp = os.path.join(job, "graphics-plan.json")
    if os.path.exists(pp):
        plan = json.load(open(pp))
        beats = plan.get("beats", [])
        cells = {str(b.get("id")): b for b in beats if b.get("graphic")}
        if plan.get("reframe"):            # V1 reframed (Motion scale over the width-fit + a vertical shift): map faces through it
            REFRAME[0], REFRAME[1] = float(plan["reframe"]["k"]), float(plan["reframe"]["dy"])
            print(f"· V1 reframe from the plan: x{REFRAME[0]} about the centre, dy {REFRAME[1]:+.0f} px")
        if plan.get("push_in_pivot_y") is not None:
            global PUSH_PIVOT_Y
            PUSH_PIVOT_Y = float(plan["push_in_pivot_y"])
    # the punch-in beats: any beat (graphic or not) flagged push_in — the V1 footage zooms there, so every
    # overlay on screen at that moment (captions, the headline, a chip) is judged against the GROWN face
    pushes = [(float(b["start"]), float(b["end"])) for b in beats if b.get("push_in") and "start" in b and "end" in b]
    cutouts = CutoutAlpha(cut_rows, seq_w, seq_h) if cut_rows else None
    if cut_rows: print(f"· {len(cut_rows)} person cut-out row(s) on the timeline: their alpha is subtracted before judging")
    report = {"job": job, "rows": [], "fails": 0, "waived": 0}
    any_fail = False
    seq_fps = None
    for r in rows:
        gid = r["id"]
        if r.get("kind") == "cutout": continue
        f = r["file"]
        if not os.path.exists(f):
            print(f"✗ {gid}: render missing {f}"); report["rows"].append({"id": gid, "status": "FAIL", "why": "render missing"}); any_fail = True; report["fails"] += 1; continue
        pr = probe(f)
        if r.get("kind") in ("full", "segment"):     # "segment" = the chat-only assemble name for an opaque full-frame part
            if pr["pix"].startswith("yuva"):
                print(f"✗ {gid}: a full-screen row must be OPAQUE (this has alpha: {pr['pix']}) — an alpha overlay written as 'full' would dodge the face sweep"); any_fail = True; report["fails"] += 1
                report["rows"].append({"id": gid, "status": "FAIL", "why": "full row with alpha"})
            continue
        if (cells.get(gid) or {}).get("kind") in UNDER_CUTOUT and not cutouts:
            print(f"✗ {gid}: a {cells[gid]['kind']} cell with NO person cut-out row on the timeline — the word/bed is bare ink on the face "
                  f"(render it: workflows/cutout.py → hf-graphics/cutout/renders/cutout-{gid}.mov, then place-graphics.py --plan --write derives the row)")
            any_fail = True; report["fails"] += 1; report["rows"].append({"id": gid, "status": "FAIL", "why": "no cutout row"}); continue
        # 9:16 renders are placed 1:1 on the 1080x1920 sequence, so their size is exact; a 16:9 overlay is scaled to
        # the base by the lane (assemble.py scales every layer), so there only the aspect has to match
        if ((pr["w"], pr["h"]) != (seq_w, seq_h)) if seq_h > seq_w else (pr["w"] * seq_h != pr["h"] * seq_w):
            print(f"✗ {gid}: render is {pr['w']}x{pr['h']}, the sequence is {seq_w}x{seq_h}"
                  + ("" if a.seq else " (read off the base cut: pass --seq WxH if the sequence is another size)")); any_fail = True; report["fails"] += 1
            report["rows"].append({"id": gid, "status": "FAIL", "why": "render size"}); continue
        seq_fps = seq_fps or pr["fps"]
        if abs(pr["fps"] - seq_fps) > 0.01:
            print(f"✗ {gid}: render fps {pr['fps']:.3f} != {seq_fps:.3f} (the first render's rate): a rate mismatch drifts every frame off its footage"); any_fail = True; report["fails"] += 1
            report["rows"].append({"id": gid, "status": "FAIL", "why": "fps"}); continue
        F = 1.0 / pr["fps"]
        zoom = PUSH_IN_ZOOM if ((cells.get(gid) or {}).get("push_in") or any(r["start"] < p1 and p0 < r["end"] for p0, p1 in pushes)) else 1.0
        # the keep-out per V1 segment the row touches (union of the faces sampled inside that segment's part of the row)
        kos = []
        for s in segs:
            lo, hi = max(r["start"], s["t0"]), min(r["end"], s["t1"])
            if hi - lo <= 1e-3: continue
            if not s["clip"]:
                print(f"✗ {gid}: the raw clip of the segment at {s['t0']:.2f}→{s['t1']:.2f}s is missing, the face there cannot be measured"); any_fail = True; report["fails"] += 1
                report["rows"].append({"id": gid, "status": "FAIL", "why": "raw clip missing"}); kos = None; break
            # the samples sit on the STEP grid in CLIP time, so every row over this footage shares the decode
            raw_lo, raw_hi = s["in"] + (lo - s["t0"]), s["in"] + (hi - s["t0"])
            times = grid(raw_lo, raw_hi)
            dets_ = det.faces(s["clip"], times)
            boxes = [to_seq(bx, seq_w, seq_h) for bx in dets_ if bx]
            # per-sample bare boxes in timeline time: what a cut-out must cover at that moment
            samples = [(s["t0"] + (tt - s["in"]), keepout([to_seq(bx, seq_w, seq_h)], seq_w, seq_h, zoom, margins=False)) for tt, bx in zip(times, dets_) if bx]
            kos.append((lo, hi, keepout(boxes, seq_w, seq_h, zoom), keepout(boxes, seq_w, seq_h, zoom, margins=False), samples))
        if kos is None: continue
        share, fi, ko, band = sweep(f, r["start"], r["end"], F, kos, seq_w, seq_h, cutouts)
        waived = (waivers.get(gid) or {}).get("face")
        status = "ok"
        if band and not (waivers.get(gid) or {}).get("zone"):
            # a FAIL since 2026-09-28 (the user's unbreakable IG safe-zone rule): key ink outside x 180→905 · y 200→1507
            # or in the button column. A prop that only passes through is waived with {"gN": {"zone": "why"}}.
            any_fail = True; report["fails"] += 1; status = "FAIL"
            print(f"✗ {gid}: solid ink in the {band[1]} at frame {band[0]} ({r['start'] + band[0] * F:.3f}s)  {os.path.basename(f)}")
        if share > TOLERANCE and not waived:
            any_fail = True; report["fails"] += 1; status = "FAIL"
            print(f"✗ {gid}: ink on the face — {share * 100:.1f}% of the keep-out x {ko[0]}→{ko[2]} y {ko[1]}→{ko[3]} at frame {fi} ({r['start'] + fi * F:.3f}s)  {os.path.basename(f)}")
        elif share > TOLERANCE:
            report["waived"] += 1; status = "waived"
            print(f"~ {gid}: waived ({waived}) — {share * 100:.1f}% at frame {fi}")
        elif status == "ok":
            print(f"✓ {gid}: clear ({share * 100:.2f}% max inside the keep-out{'' if ko else ', no face in its window'}{', push-in zoom' if zoom != 1.0 else ''})  {os.path.basename(f)}")
        report["rows"].append({"id": gid, "status": status, "share": share, "frame": fi, "time": r["start"] + max(fi, 0) * F, "keepout": ko,
                               "band": band, "why": waived})
    n = len(report["rows"])
    print(f"{'FACE LAW BROKEN' if any_fail else 'FACE CLEAR'}: {n} rows judged, {report['fails']} FAIL, {report['waived']} waived")
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)) or ".", exist_ok=True)
        json.dump(report, open(a.json, "w"), indent=1)
    sys.exit(1 if any_fail else 0)


# ── selftest ─────────────────────────────────────────────────────────────────
def selftest():
    ok = True
    def check(name, cond):
        nonlocal ok
        print(f"  {'✓' if cond else '✗'} {name}"); ok = ok and bool(cond)
    # mapping: a 720x1280 clip fills the width of a 1080x1920 sequence (x1.5, no offset); a 1080x1920 clip is 1:1
    check("to_seq 720x1280 → x1.5", to_seq((100, 200, 50, 60, 720, 1280), 1080, 1920) == (150.0, 300.0, 75.0, 90.0))
    check("to_seq 1080x1920 → identity", to_seq((100, 200, 50, 60, 1080, 1920), 1080, 1920) == (100.0, 200.0, 50.0, 60.0))
    # union never shrinks; margins applied; zoom grows about the centre
    ko = keepout([(400, 800, 300, 400), (380, 780, 300, 400)], 1080, 1920)
    check("keepout is the union + margins", ko == [380 - MARGIN_SIDE, 780 - MARGIN_TOP, 700 + MARGIN_SIDE, 1200 + MARGIN_BOTTOM])
    kz = keepout([(400, 800, 300, 400)], 1080, 1920, PUSH_IN_ZOOM)
    check("zoom widens the keep-out", kz[1] < ko[1] and kz[3] > ko[3])
    check("no boxes → no keep-out", keepout([], 1080, 1920) is None)
    z = zones_for([170, 671, 814, 1454], 1080, 1920)
    check("IG zones for a high head: above only (below < 120 px to y 1507, no side ≥ 260 px inside x 180→905)", z["above"] == [180, 200, 905, 671] and z["below"] is None and z["left"] is None and z["right"] is None)
    check("grid shares samples across rows", grid(3.7, 6.0) == [3.75, 4.0, 4.25, 4.5, 4.75, 5.0, 5.25, 5.5, 5.75, 6.0] and len(grid(1.01, 1.02)) == 1)
    # synthetic renders: a solid box ON the face, one BESIDE it, one in the top platform band, one under a cut-out
    tmp = tempfile.mkdtemp()
    def synth(name, boxes, alpha=1.0):
        # the alpha plane is drawn as LUMA on a black mask (drawbox lives in YUV space and would drop an rgba alpha),
        # then merged onto a white colour plane: a straight-alpha ProRes exactly like a real overlay render
        g = int(round(alpha * 255))
        mask = "".join(f",drawbox=x={x}:y={y}:w={w}:h={h}:color=0x{g:02x}{g:02x}{g:02x}:t=fill" for x, y, w, h in boxes)
        out = os.path.join(tmp, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=white:s=1080x1920:r=30000/1001:d=0.5",
                        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30000/1001:d=0.5",
                        "-filter_complex", f"[1]format=gray{mask},format=gray[m];[0]format=rgba[c];[c][m]alphamerge,format=yuva444p10le[o]",
                        "-map", "[o]", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", out], check=True)
        return out
    F = 1001 / 30000; kos = [(0.0, 0.5, [170, 671, 814, 1454])]
    on = synth("on.mov", [(400, 900, 300, 200)]); beside = synth("beside.mov", [(200, 300, 600, 200)])
    band = synth("band.mov", [(100, 40, 800, 100)]); faint = synth("faint.mov", [(400, 900, 300, 200)], 0.35)
    s_on = sweep(on, 0, 0.5, F, kos, 1080, 1920); s_beside = sweep(beside, 0, 0.5, F, kos, 1080, 1920)
    s_band = sweep(band, 0, 0.5, F, kos, 1080, 1920); s_faint = sweep(faint, 0, 0.5, F, kos, 1080, 1920)
    check(f"a box on the face fails ({s_on[0] * 100:.1f}% > tolerance)", s_on[0] > TOLERANCE)
    check(f"a box beside the face passes ({s_beside[0] * 100:.2f}%)", s_beside[0] <= TOLERANCE and s_beside[3] is None)
    col = synth("col.mov", [(880, 1000, 150, 150)]); edge = synth("edge.mov", [(40, 600, 120, 120)])
    check("a box under IG's button column is a zone hit", sweep(col, 0, 0.5, F, kos, 1080, 1920)[3] is not None)
    check("a box in the cropped left edge (x < 180) is a zone hit", sweep(edge, 0, 0.5, F, kos, 1080, 1920)[3] is not None)
    check("solid ink in the top band is reported", s_band[3] is not None and "danger" in s_band[3][1])
    check(f"a 0.35-opacity texture over the face still counts ({s_faint[0] * 100:.1f}%)", s_faint[0] > TOLERANCE)
    cover = synth("cutout.mov", [(150, 650, 700, 850)])        # a cut-out covering the whole keep-out
    co = CutoutAlpha([{"file": cover, "start": 0.0, "end": 0.5}], 1080, 1920)
    s_under = sweep(on, 0, 0.5, F, kos, 1080, 1920, co)
    check(f"ink under a cut-out is subtracted ({s_under[0] * 100:.2f}%)", s_under[0] <= TOLERANCE)
    # a bed beside the head (inside the margins, outside the bare face box) is the design once a cut-out covers the face
    beside_hair = synth("hair.mov", [(170, 671, 60, 780)])          # a strip in the left margin of the keep-out
    kos_b = [(0.0, 0.5, [170, 671, 814, 1454], [240, 811, 744, 1404], [(0.25, [240, 811, 744, 1404])])]
    check("a bed strip in the keep-out MARGIN fails without a cut-out", sweep(beside_hair, 0, 0.5, F, kos_b, 1080, 1920)[0] > TOLERANCE)
    check("…and passes once a cut-out covers the face (the silhouette is the boundary)", sweep(beside_hair, 0, 0.5, F, kos_b, 1080, 1920, co)[0] <= TOLERANCE)
    weak = synth("weak.mov", [(150, 650, 700, 300)])                # a cut-out that covers only the top of the face box: the mask failed
    co_w = CutoutAlpha([{"file": weak, "start": 0.0, "end": 0.5}], 1080, 1920)
    check("a cut-out that fails to cover the face does not excuse ink on it", sweep(on, 0, 0.5, F, kos_b, 1080, 1920, co_w)[0] > TOLERANCE)
    print("SELFTEST", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)


def main():
    if "--selftest" in sys.argv: selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("zones"); z.add_argument("video"); z.add_argument("--from", dest="t0", type=float, default=0.0)
    z.add_argument("--to", dest="t1", type=float, default=None); z.add_argument("--step", type=float, default=STEP)
    z.add_argument("--seq", default="1080x1920"); z.add_argument("--zoom", type=float, default=1.0); z.add_argument("--min-face", type=float, default=MIN_FACE)
    z.add_argument("--json", action="store_true"); z.add_argument("--annotate")
    z.add_argument("--reframe", help="K,DY: V1 reframed by Motion scale K over the width-fit and shifted DY px (plan 'reframe')")
    z.add_argument("--pivot", type=float, help="punch-in pivot y (the eyeline) for --zoom; default the frame centre")
    c = sub.add_parser("check"); c.add_argument("job"); c.add_argument("--ids"); c.add_argument("--json")
    c.add_argument("--seq", default=None, help="WxH; default: read off the base cut (see base_frame)")
    c.add_argument("--min-face", type=float, default=MIN_FACE)
    a = ap.parse_args()
    (cmd_zones if a.cmd == "zones" else cmd_check)(a)


if __name__ == "__main__":
    main()
