#!/usr/bin/env python3
"""find-fillers.py: filler candidates the transcript cannot show — a cut sheet for step 2, never a cut.

  python3 .claude/skills/rough-cut/scripts/find-fillers.py projects/<job>            # human list
  python3 .claude/skills/rough-cut/scripts/find-fillers.py projects/<job> --json     # machine-readable

Why (2026-09-25). Whisper drops hesitation sounds from its text: a Spanish "eh…", "mmm", "este…" held
between two words simply is not in words.json, so a transcript-only rough cut leaves every one of
them in. Their footprint is still there: a GAP between two aligned words that is not silent. This
script lists two kinds of candidates, each with its raw-clip time range, for the editor to decide:

  hidden   a gap > 150 ms between aligned words containing ≥ 120 ms of voiced audio well above the
           room tone. Usually "eh"/"mmm"/a breathy restart; sometimes a real word the aligner missed,
           so it is a CANDIDATE — confirm by ear or by re-transcribing the slice before cutting.
  marker   a Spanish discourse marker ("este", "o sea", "bueno", "pues", "¿no?", "tipo", "digamos",
           "en plan", "básicamente", "¿sabes?", "¿vale?") followed by a pause ≥ 250 ms, a comma or "…".
           Inside a construction ("este video", "bueno para") it is never listed, even sentence-initial.
  always   "eh", "em", "mmm", "ehh", "um", "uh" when Whisper did write them: always safe to cut.

Nothing is cut here. The rough-cut editor reads the list, keeps what carries meaning, and writes the
cuts into cuts.json like any other edit (rough-cut SKILL.md § fillers).
"""
import argparse, json, math, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from array import array
from pathlib import Path

SR = 16000
HOP = 0.010                 # 10 ms RMS frames
MIN_GAP = 0.150             # gap between aligned words worth inspecting
MIN_VOICED = 0.120          # voiced time inside the gap that makes it a candidate
EDGE = 0.040                # ignore the first/last 40 ms of a gap (word tails, aligner slack)
OVER_FLOOR_DB = 14.0        # voiced = at least this far above the clip's room tone
UNDER_SPEECH_DB = 8.0       # ...and no more than this far under the median level of the aligned words
MARKER_PAUSE = 0.250
ALWAYS = {"eh", "ehh", "em", "emm", "mmm", "mm", "um", "uh", "uhm", "ah"}
MARKERS_1 = {"este", "bueno", "pues", "tipo", "digamos", "básicamente", "basicamente", "no", "sabes", "vale"}
MARKERS_2 = {("o", "sea"), ("en", "plan")}
TAG_ONLY = {"no", "sabes", "vale"}          # only as a question tag: "¿no?", "¿sabes?", "¿vale?"


def norm(t):
    return re.sub(r"[^\wáéíóúüñ]", "", (t or "").lower())


def rms_frames(path):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0", "-vn", "-ac", "1",
                          "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    if not raw:
        return None
    pcm = array("h"); pcm.frombytes(raw[: len(raw) // 2 * 2])
    n = int(SR * HOP)
    out = []
    for i in range(0, len(pcm) - n, n):
        seg = pcm[i:i + n]
        e = sum(x * x for x in seg) / n
        out.append(10 * math.log10(e / (32768.0 ** 2) + 1e-12))
    return out


def text_of(w):
    return w.get("w") or w.get("word") or w.get("text") or ""


def analyse(clip_path, words):
    db = rms_frames(clip_path)
    if not db:
        return [], None
    floor = sorted(db)[int(len(db) * 0.15)]
    ws = [w for w in words if "start" in w and "end" in w]
    # Threshold relative to the SPEECH, not the room: a phone mic's room tone can sit 60 dB under the
    # voice, so "above the floor" catches every breath and rustle (first real run: 22 hits in 50 s).
    # A hesitation "eh"/"mmm" is spoken at nearly the voice's own level; breaths sit 15-25 dB under it.
    sp = sorted(db[k] for w in ws for k in range(int(w["start"] / HOP), min(int(w["end"] / HOP), len(db))))
    speech = sp[len(sp) // 2] if sp else floor + 30
    thr = max(floor + OVER_FLOOR_DB, speech - UNDER_SPEECH_DB)
    rows = []
    for i, w in enumerate(ws):
        t = norm(text_of(w))
        raw_t = text_of(w)
        prev_gap = w["start"] - ws[i - 1]["end"] if i else 99
        next_gap = ws[i + 1]["start"] - w["end"] if i + 1 < len(ws) else 99
        prev_end = i == 0 or text_of(ws[i - 1]).rstrip().endswith((".", "?", "!", "…"))
        if t in ALWAYS:
            rows.append(dict(kind="always", start=w["start"], end=w["end"], text=raw_t))
        elif t in MARKERS_1:
            is_tag = raw_t.strip().endswith("?")
            if t in TAG_ONLY and not is_tag:
                pass
            # A marker needs a break AFTER it (a pause, a comma, "…"). Being sentence-initial is not enough:
            # "Este agente de facturación…" opens with the demonstrative, 20 ms before its noun, and a list
            # that flagged it would cut the video's first word (c3, 2026-09-25).
            elif is_tag or next_gap >= MARKER_PAUSE or raw_t.rstrip().endswith((",", "…", "...")):
                rows.append(dict(kind="marker", start=w["start"], end=w["end"], text=raw_t))
        if i + 1 < len(ws) and (t, norm(text_of(ws[i + 1]))) in MARKERS_2:
            nw = ws[i + 1]
            after = ws[i + 2]["start"] - nw["end"] if i + 2 < len(ws) else 99
            if after >= MARKER_PAUSE or text_of(nw).rstrip().endswith((",", "…", "...")):
                rows.append(dict(kind="marker", start=w["start"], end=nw["end"], text=f"{raw_t} {text_of(nw)}"))
        if i + 1 < len(ws):
            a, b = w["end"] + EDGE, ws[i + 1]["start"] - EDGE
            if ws[i + 1]["start"] - w["end"] >= MIN_GAP and b > a:
                fa, fb = int(a / HOP), int(b / HOP)
                voiced = [k for k in range(fa, min(fb, len(db))) if db[k] > thr]
                if len(voiced) * HOP >= MIN_VOICED:
                    rows.append(dict(kind="hidden", start=round(voiced[0] * HOP, 3), end=round((voiced[-1] + 1) * HOP, 3),
                                     text=f"(sin transcribir entre «{raw_t}» y «{text_of(ws[i + 1])}»)",
                                     voiced_ms=int(len(voiced) * HOP * 1000),
                                     peak_vs_speech_db=round(max(db[k] for k in voiced) - speech, 1),
                                     # voice running right up to the next word is usually that word's real
                                     # onset starting before the aligner's timestamp ("A-I" spelled out), not a filler
                                     # Only a SHORT block (≤ 300 ms) glued to the next word counts: a real "ehh" also
                                     # runs into the next word, but it is usually longer (first test: 480 ms, 1370 ms).
                                     likely_word_onset=(fb - 1 - voiced[-1] <= 2 and len(voiced) * HOP <= 0.300
                                                        and (voiced[-1] - voiced[0] + 1) - len(voiced) <= 5)))   # ≤ 50 ms dip inside: spelled "A-I"
    return rows, round(floor, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("job")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    job = Path(a.job).resolve()
    wp = job / "transcript" / "words.json"
    if not wp.is_file():
        raise SystemExit(f"✗ no {wp}: run transcribe.sh first")
    data = json.loads(wp.read_text())
    report = []
    for c in data.get("clips", []):
        if c.get("no_speech"):
            continue
        name = c.get("clip") or c.get("file") or Path(c.get("path", "")).name
        cands = [Path(c.get("path", "")), job / "raw" / name]
        cands += sorted((job / "raw").glob(Path(name).stem + ".*"))
        clip = next((p for p in cands if p and p.is_file()), None)
        if clip is None:
            print(f"· {name}: raw clip not found, skipped", file=sys.stderr)
            continue
        rows, floor = analyse(clip, c.get("words", []))
        report.append(dict(clip=name, room_tone_db=floor, candidates=rows))
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    total = 0
    for r in report:
        print(f"{r['clip']}  (room tone {r['room_tone_db']} dBFS)")
        for x in r["candidates"]:
            total += 1
            extra = (f"  {x['voiced_ms']} ms voiced, {x['peak_vs_speech_db']:+} dB vs voice"
                     + ("  ⚠ may be the next word's onset — listen before cutting" if x.get("likely_word_onset") else "")
                     ) if x["kind"] == "hidden" else ""
            print(f"  {x['kind']:<6} {x['start']:8.3f}–{x['end']:.3f}  {x['text']}{extra}")
    print(f"{total} candidate(s). Nothing was cut: decide each one, keep what carries meaning, then edit cuts.json.")


if __name__ == "__main__":
    main()
