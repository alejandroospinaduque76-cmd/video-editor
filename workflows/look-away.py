#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mediapipe==0.10.14", "opencv-python-headless", "numpy"]
# ///
"""look-away.py — find where the speaker's eyes leave the lens inside each kept segment (the user's rule, 2026-09-28:
"corta las partes donde la persona mira a otro lado para que los viewers no pierdan el hilo"), sideways AND up/down
(reading a script above or below the camera: the owner's VSL, 2026-09-29).

  uv run workflows/look-away.py projects/<job>                        # strip per segment + suggested trims
  uv run workflows/look-away.py projects/<job> --json out.json
  uv run workflows/look-away.py projects/<job> --write <proposed.json> # + an EDL with the head/tail look-aways trimmed

Method: MediaPipe FaceMesh with iris landmarks at 10 fps over the raw clip (ffmpeg's fps filter keeps container
time), scaled keeping the clip's own aspect (a 16:9 take is read at 1280x720, a 9:16 one at 540x960: the old fixed
540x960 squeezed a landscape face until FaceMesh found none, and said nothing — the owner's 4K VSL, 2026-09-29).
Per sample:
  sideways  2 x (iris position along the eye − the clip's median) + head yaw (nose vs eye midpoint, inter-ocular units)
  vertical  2 x (iris height between the lids − the clip's median) + head pitch (nose below the eye line, same units)
  blink     the eye closes: its opening (lid to lid over corner to corner) under half the clip's median. A look up or
            down keeps the eye open, so it is no longer mistaken for a blink (it was: reading upward read as `b`).
Thresholds are relative to the clip's own medians, so a face that sits slightly turned for the whole take is neutral.

Strip legend, one character per 0.1 s: `.` on the lens · `r`/`l` mild glance right/left · `R`/`L` clear look-away ·
`u`/`d` mild glance up/down · `U`/`D` clear look up/down (reading) · `b` blink · `?` no face found.
A head turn that keeps the iris on the lens stays `.` — only where the eyes point decides.

What to do with a flag: --write trims only the SILENCE a look-away sits in at a segment head or tail (before the
first word, after the last one, from transcript/words.json) and never deletes a word. A look-away over spoken words,
at an edge or mid-sentence, is LISTED with those words: whether the sentence still reads without them is an editing
call (cut the phrase, hide it under a cutaway, or keep it), made by the editor and the creator, never by this tool.
On the owner's VSL (6c, 2026-09-29) the old word-boundary trims removed kept words ('Y no solo', 'videos.', 'compren')
in 5 of 6 proposals, while the phrases he did cut ('con una garantía', read looking up) sat under clear U runs. --write
never touches transcript/cuts.json: it writes the proposal where you say, to review and then splice like any EDL.
"""
import json, os, subprocess, sys, statistics as st
import numpy as np

AWAY = "rRlLuUdD"
CLEAR = "RLUD"
MIN_CLEAR_EDGE, MIN_CLEAR_MID = 2, 3     # clear samples (0.1 s each) a run needs to be flagged at an edge / mid-sentence


def away_runs(strip):
    """[(i0, i1)] index ranges of look-away in a strip: away samples, blinks inside them, and a single on-lens or
    unread sample between two away ones (FaceMesh drops a frame; a strip ending 'UUUUUUU.' is still a tail look-away),
    each run holding at least MIN_CLEAR_EDGE clear samples. Blinks at a run's edges are not part of it."""
    n = len(strip)
    m = [ch in AWAY or ch == "b" for ch in strip]
    for i in range(1, n - 1):
        if not m[i] and strip[i - 1] in AWAY and strip[i + 1] in AWAY:
            m[i] = True
    if n >= 2 and not m[-1] and strip[-2] in AWAY:
        m[-1] = True
    if n >= 2 and not m[0] and strip[1] in AWAY:
        m[0] = True
    out, i = [], 0
    while i < n:
        if not m[i]:
            i += 1; continue
        j = i
        while j < n and m[j]:
            j += 1
        a, b = i, j
        while a < b and strip[a] == "b":
            a += 1
        while b > a and strip[b - 1] == "b":
            b -= 1
        if sum(ch in CLEAR for ch in strip[a:b]) >= MIN_CLEAR_EDGE:
            out.append((a, b))
        i = j
    return out


def display_size(video):
    """The frame as it plays: a phone raw stores its landscape size with a ±90 rotation."""
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:stream_side_data=rotation", "-of", "json", video],
                                  capture_output=True, text=True).stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    w, h = int(s.get("width", 1080)), int(s.get("height", 1920))
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def read_clip(video, mp):
    w0, h0 = display_size(video)
    W, H = (1280, 720) if w0 > h0 else (540, 960)
    W, H = (W, round(W * h0 / w0 / 2) * 2) if w0 > h0 else (round(H * w0 / h0 / 2) * 2, H)
    STEP = 0.1
    fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True,
                                         min_detection_confidence=0.5)
    proc = subprocess.Popen(["ffmpeg", "-v", "quiet", "-i", video, "-vf", f"fps={1 / STEP},scale={W}:{H}", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    rows, i = [], 0
    while True:
        buf = proc.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        r = fm.process(img); t = round(i * STEP, 2); i += 1
        if not r.multi_face_landmarks:
            rows.append(dict(t=t)); continue
        L = r.multi_face_landmarks[0].landmark
        P = lambda k: np.array([L[k].x * W, L[k].y * H])
        re_o, re_i, le_i, le_o, ir_r, ir_l, nose = P(33), P(133), P(362), P(263), P(468), P(473), P(1)
        mid = (re_o + le_o) / 2; iod = max(1e-3, float(np.linalg.norm(le_o - re_o)))
        along = lambda o, inn, iris: float(np.dot(iris - o, inn - o) / max(1e-6, np.linalg.norm(inn - o) ** 2))
        vr = lambda up, lo, iris: float((iris[1] - P(up)[1]) / max(1e-3, P(lo)[1] - P(up)[1]))
        opening = lambda up, lo, a, b: float((P(lo)[1] - P(up)[1]) / max(1e-3, np.linalg.norm(P(b) - P(a))))
        rows.append(dict(t=t, yaw=float((nose[0] - mid[0]) / iod), pitch=float((nose[1] - mid[1]) / iod),
                         gx=(along(re_o, re_i, ir_r) + 1 - along(le_i, le_o, ir_l)) / 2,
                         gy=(vr(159, 145, ir_r) + vr(386, 374, ir_l)) / 2,
                         ear=(opening(159, 145, 33, 133) + opening(386, 374, 362, 263)) / 2,
                         eye_y=float(mid[1] / H)))
    proc.wait()
    return rows, (W, H), (w0, h0)


def smooth(rows, med, half=2):
    """Per sample, the sideways (d) and vertical (v) offsets from the clip's medians, each the median of the samples
    within ±half (0.2 s) that have a face and are not blinks. FaceMesh jitters by more than a mild glance from frame
    to frame; on the owner's 16:9 VSL the unsmoothed strip flagged a third of the samples it kept."""
    raw = []
    for x in rows:
        if "yaw" not in x or (med.get("ear") and x["ear"] < 0.5 * med["ear"]):
            raw.append(None); continue
        raw.append((2 * (x["gx"] - med["gx"]) + (x["yaw"] - med["yaw"]),
                    2 * (x["gy"] - med["gy"]) + (x["pitch"] - med["pitch"])))
    for i, x in enumerate(rows):
        win = [r for r in raw[max(0, i - half): i + half + 1] if r is not None]
        if raw[i] is not None and win:
            x["d"], x["v"] = st.median(r[0] for r in win), st.median(r[1] for r in win)


def classify(x, med):
    if "yaw" not in x:
        return "?"
    if med.get("ear") and x["ear"] < 0.5 * med["ear"]:
        return "b"
    d, v = x.get("d", 0.0), x.get("v", 0.0)
    if abs(d) >= abs(v):
        return "R" if d > 0.08 else "r" if d > 0.05 else "L" if d < -0.08 else "l" if d < -0.05 else "."
    return "D" if v > 0.16 else "d" if v > 0.10 else "U" if v < -0.16 else "u" if v < -0.10 else "."


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    job = a[0]
    segs = json.load(open(os.path.join(job, "transcript", "cuts.json"), encoding="utf-8"))["segments"]
    clips = sorted({s["clip"] for s in segs})
    import mediapipe as mp
    out = {}
    for clip in clips:
        rows, (W, H), (w0, h0) = read_clip(os.path.join(job, "raw", clip), mp)
        kept = [x for x in rows if "yaw" in x and any(s["clip"] == clip and s["start"] <= x["t"] <= s["end"] for s in segs)]
        inseg = [x for x in rows if any(s["clip"] == clip and s["start"] <= x["t"] <= s["end"] for s in segs)]
        med = {k: st.median(x[k] for x in kept) for k in ("yaw", "pitch", "gx", "gy", "ear", "eye_y")} if kept else {}
        seen = len(kept) / max(1, len(inseg))
        if seen < 0.6:
            print(f"⚠ {clip}: a face was found in only {100 * seen:.0f}% of the kept samples ({w0}x{h0} read at {W}x{H}): "
                  "this clip cannot be judged; check the look-aways by eye", file=sys.stderr)
        if med:
            smooth(rows, med)
        out[clip] = dict(median=med, rows=rows, seen=round(seen, 3))
    words = load_words(job)
    report = []
    for i, s in enumerate(segs):
        c = out[s["clip"]]; med = c["median"]
        cells = [x for x in c["rows"] if s["start"] - 1e-3 <= x["t"] <= s["end"] + 1e-3]
        strip = "".join(classify(x, med) for x in cells)
        t_of = lambda k: cells[k]["t"] if k < len(cells) else float(s["end"])
        ws = [w for w in words.get(os.path.basename(s["clip"]), []) if w["end"] > s["start"] and w["start"] < s["end"]]
        head = tail = None; mid = []
        for i0, i1 in away_runs(strip):
            t0 = float(s["start"]) if i0 <= 1 else t_of(i0)
            t1 = float(s["end"]) if i1 >= len(strip) - 1 else t_of(i1)
            said = [w for w in ws if w["end"] > t0 + 0.02 and w["start"] < t1 - 0.02]
            run = dict(start=round(t0, 2), end=round(t1, 2), strip=strip[i0:i1], words=" ".join(word_text(w) for w in said))
            if i0 <= 1 and head is None:
                head = run
            elif i1 >= len(strip) - 1:
                tail = run
            elif sum(ch in CLEAR for ch in strip[i0:i1]) >= MIN_CLEAR_MID:
                mid.append(run)
        report.append(dict(seg=i, clip=s["clip"], start=s["start"], end=s["end"], strip=strip, head=head, tail=tail, mid=mid,
                           head_away_s=round(head["end"] - head["start"], 1) if head else 0.0,
                           tail_away_s=round(tail["end"] - tail["start"], 1) if tail else 0.0,
                           mid_away=len(mid)))
        flag = "".join(f"  ⚠ {k} {r['start']:.2f}-{r['end']:.2f}" + (f" over '{r['words']}'" if r["words"] else " (silence)")
                       for k, r in (("HEAD", head), ("TAIL", tail)) if r)
        flag += "".join(f"  ⚠ MID {r['start']:.2f}-{r['end']:.2f} over '{r['words'] or '(silence)'}'" for r in mid)
        print(f"seg{i:2d} {s['start']:7.2f}-{s['end']:7.2f} {strip}{flag}")
    print("eye line (median, normalised y on the raw): " + ", ".join(f"{k}: {v['median'].get('eye_y', 0):.3f}" for k, v in out.items()))
    if "--json" in a:
        json.dump(dict(segments=report, clips={k: dict(median=v["median"], face_seen=v["seen"]) for k, v in out.items()}),
                  open(a[a.index("--json") + 1], "w", encoding="utf-8"), indent=1)
    if "--write" in a:
        write_proposal(segs, report, words, a[a.index("--write") + 1])


def load_words(job):
    """{clip basename: words} from transcript/words.json ({} when there is none)."""
    wp = os.path.join(job, "transcript", "words.json")
    words = {}
    if os.path.exists(wp):
        for c in json.load(open(wp, encoding="utf-8")).get("clips", []):
            words[os.path.basename(c.get("clip") or c.get("file") or "")] = c.get("words", [])
    return words


def word_text(w):
    return str(w.get("word", w.get("w", w.get("text", "")))).strip()


def write_proposal(segs, report, words, dest):
    """The EDL with the SILENCE of each head / tail look-away trimmed: a head look-away before the first word moves
    the start to 40 ms before that word, a tail one after the last word moves the end to 70 ms after it (the kit's
    word pads), and a trim under 0.1 s or one leaving under 0.5 s is not made. A word is never removed: a look-away
    over words is listed under `review` with those words. transcript/cuts.json is never touched."""
    new, changed, review = [], 0, []
    for s, r in zip(segs, report):
        ns, a, b = dict(s), float(s["start"]), float(s["end"])
        ws = [w for w in words.get(os.path.basename(s["clip"]), []) if w["end"] > a and w["start"] < b]
        if not ws:
            new.append(ns); continue
        if r["head"]:
            to = min(r["head"]["end"], ws[0]["start"] - 0.04)
            if to - a >= 0.1 and b - to >= 0.5:
                ns["start"] = round(to, 3)
        if r["tail"]:
            fr = max(r["tail"]["start"], ws[-1]["end"] + 0.07)
            if b - fr >= 0.1 and fr - float(ns["start"]) >= 0.5:
                ns["end"] = round(fr, 3)
        if (ns["start"], ns["end"]) != (s["start"], s["end"]):
            changed += 1
            print(f"  seg{r['seg']}: {a:.3f}-{b:.3f} → {ns['start']:.3f}-{ns['end']:.3f} (silence under a look-away; no word removed)")
        for k in ("head", "tail"):
            if r[k] and r[k]["words"]:
                review.append(dict(seg=r["seg"], where=k, **r[k]))
        review += [dict(seg=r["seg"], where="mid", **m) for m in r["mid"]]
        new.append(ns)
    json.dump(dict(segments=new, review=review), open(dest, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if not words:
        print("⚠ no transcript/words.json: nothing trimmed (a trim that cannot see the words could cut one)")
    print(f"→ {dest}: {changed} segment(s) trimmed, silence only; transcript/cuts.json untouched")
    if review:
        print(f"  {len(review)} look-away(s) over spoken words, NOT cut (in the file's `review`): cut the phrase if the "
              "sentence reads without it, hide it under a cutaway, or keep it")
        for x in review:
            print(f"    seg{x['seg']} {x['where']:4s} {x['start']:.2f}-{x['end']:.2f} {x['strip']}  '{x['words']}'")


if __name__ == "__main__":
    main()
