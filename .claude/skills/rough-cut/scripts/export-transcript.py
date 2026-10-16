#!/usr/bin/env python3
"""export-transcript.py — derive a cut-aligned caption transcript from the SAME
WhisperX large-v3 words used for the rough cut. NO re-transcription.

The rough cut transcribes the RAW footage (raw timeline). Captions need the
transcript aligned to the CUT output (a reordered subset of raw segments). Since
cuts.json records exactly which raw segments survived and in what order, we remap
the kept words to the output timeline arithmetically — same large-v3 quality,
correct timings, zero extra ML.

This is ALSO where transcription mistakes get fixed. Because this script writes
the canonical transcript (outputs/<job>.transcript.json) — the single source of
truth every downstream step reads (graphics-plan, captions, both formats) — the
spelling/brand corrections in transcript-corrections.json are applied HERE,
once, so the fix propagates everywhere instead of being patched per caption build.
'auto' entries are replaced silently; 'flag' entries are printed for eyeballing.

Output shape is {language_code, words:[{text,start,end,type}]} in seconds —
the format HyperFrames caption tooling treats as already-normalized, so any
consumer skips its own whisper pass.

usage: export-transcript.py <words.json> <cuts.json> <out.json> [corrections.json]
"""
import json
import os
import pathlib
import re
import sys
# Windows consoles/pipes default to cp1252, which can't encode the ⚠/→ glyphs in this
# script's status lines: a cosmetic print must never kill a pipeline step (it did once,
# 2026-08-13, mid-splice on a real Windows job). Force UTF-8; no-op on macOS/Linux.
for _s in (sys.stdout, sys.stderr):
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


# leading punct / core / trailing punct — matches presets/instagram/talking-head-explainer/captions.py (join_units)
_SPLIT = re.compile(r"^(\W*)(.*?)(\W*)$")


def find_corrections(out_path, explicit):
    """Locate the corrections dictionary. Anchored on the canonical project layout
    (<repo>/projects/<job>/outputs/<job>.transcript.json), which is invariant — so
    it works no matter where this skill is installed. Falls back gracefully."""
    candidates = []
    if explicit:
        candidates.append(pathlib.Path(explicit))
    env = os.environ.get("TRANSCRIPT_CORRECTIONS") or os.environ.get("CAPTION_CORRECTIONS")
    if env:
        candidates.append(pathlib.Path(env))
    # the file is repo-ROOT config, not a preset: four different consumers read it
    # (this script, scan-transcript.py, and both caption builders), so it belongs to
    # none of them. Legacy presets/ path kept last so an older tree still resolves.
    LEGACY = ("presets", "caption-corrections.json")
    out = pathlib.Path(out_path).resolve()
    # out = <repo>/projects/<job>/outputs/<file> → parents[3] = <repo>
    if len(out.parents) >= 4:
        candidates.append(out.parents[3] / "transcript-corrections.json")
        candidates.append(out.parents[3].joinpath(*LEGACY))
    # fallback: derive repo from this script's vendored location (…/.claude/skills/rough-cut/scripts/)
    here = pathlib.Path(__file__).resolve()
    if len(here.parents) >= 5:
        candidates.append(here.parents[4] / "transcript-corrections.json")
        candidates.append(here.parents[4].joinpath(*LEGACY))
    for c in candidates:
        if c and c.exists():
            return c
    return None


def profile_vocabulary():
    """The active style profile's vocabulario {auto, flag} (workflows/profile.py, v1.3), lowercased.
    Empty with no profile or when profile.py cannot be loaded — never breaks the export."""
    try:
        import importlib.util
        kit = pathlib.Path(__file__).resolve().parents[4]
        spec = importlib.util.spec_from_file_location("ve_profile", kit / "workflows" / "profile.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        voc = mod.load()["valores"].get("vocabulario") or {}
        return ({str(k).lower(): v for k, v in (voc.get("auto") or {}).items()},
                {str(w).lower() for w in (voc.get("flag") or [])})
    except Exception:
        return {}, set()


def load_corrections(out_path, explicit):
    """Returns (AUTO dict lowercased-key→replacement, FLAG set lowercased).
    Merges an optional per-job override at <job>/corrections.local.json so a single
    video can carry context-specific fixes (e.g. a word that is only a mishear in
    THIS clip's context) without loosening the shared, conservative map."""
    path = find_corrections(out_path, explicit)
    auto, flag = {}, set()
    if path:
        cfg = json.load(open(path, encoding="utf-8"))
        auto = {k.lower(): v for k, v in cfg.get("auto", {}).items()}
        flag = {w.lower() for w in cfg.get("flag", [])}
        print(f"[export-transcript] corrections ← {path}")
    else:
        print("[export-transcript] no transcript-corrections.json found — skipping fixes")
    # v1.3: the creator's own vocabulary (profile.py `word`) wins over the shared map;
    # the per-job local file below still wins over both.
    pauto, pflag = profile_vocabulary()
    if pauto or pflag:
        auto.update(pauto)
        flag = (flag | pflag) - set(pauto)
        print(f"[export-transcript] + vocabulario del perfil ({len(pauto)} auto, {len(pflag)} flag)")
    # per-job local override sits in the job folder: <repo>/projects/<job>/corrections.local.json
    parents = pathlib.Path(out_path).resolve().parents
    if len(parents) >= 2:
        local = parents[1] / "corrections.local.json"
        if local.exists():
            lc = json.load(open(local, encoding="utf-8"))
            auto.update({k.lower(): v for k, v in lc.get("auto", {}).items()})
            flag = (flag | {w.lower() for w in lc.get("flag", [])}) - set(auto)
            print(f"[export-transcript] + per-job overrides ← {local}")
    return auto, flag


def fix_word(text, auto, flag):
    """Returns (corrected_text, note). note is ('auto', orig, new) | ('flag', orig) | None.
    Preserves surrounding punctuation; matches whole core word, case-insensitive."""
    pre, core, post = _SPLIT.match(text).groups()
    low = core.lower()
    if low in auto:
        return pre + auto[low] + post, ("auto", core, auto[low])
    if low in flag:
        return text, ("flag", core)
    return text, None


def transcript_language(wdata):
    """Language of the whole transcript, taken from what WhisperX detected per clip.
    2026-09-25: this used to be hard-coded "en", so a Spanish video was labelled English
    and every consumer that keys on language_code (caption <html lang>, the dictionary
    check in scan-transcript.py) behaved as if it were English. If clips disagree (a
    stray English insert in a Spanish talk), the language with the most WORDS wins —
    one short clip must not relabel the whole video. no_speech clips carry no words,
    so they cast no vote. Falls back to a top-level "language", then "en"."""
    votes = {}
    for clip in wdata.get("clips", []):
        if clip.get("no_speech"):
            continue
        lang = (clip.get("language") or "").strip().lower()
        if not lang:
            continue
        votes[lang] = votes.get(lang, 0) + len(clip.get("words") or [])
    if votes:
        return max(votes.items(), key=lambda kv: kv[1])[0]
    return (str(wdata.get("language") or "en")).strip().lower() or "en"


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit("usage: export-transcript.py <words.json> <cuts.json> <out.json> [corrections.json]")
    words_path, cuts_path, out_path = sys.argv[1:4]
    corrections_arg = sys.argv[4] if len(sys.argv) == 5 else None

    with open(words_path, encoding="utf-8") as f:
        wdata = json.load(f)
    with open(cuts_path, encoding="utf-8") as f:
        cuts = json.load(f)

    auto, flag = load_corrections(out_path, corrections_arg)

    # index raw words by clip basename, preserving transcript order.
    # 2026-09-25: a clip may be recorded as {"no_speech": true} with zero words (b-roll,
    # silent inserts) — `or []` keeps it in the index with nothing to remap, never a crash.
    by_clip = {}
    for clip in wdata.get("clips", []):
        if not clip.get("clip"):
            continue
        by_clip[os.path.basename(clip["clip"])] = clip.get("words") or []

    language = transcript_language(wdata)

    out_words = []
    cursor = 0.0  # running position on the OUTPUT timeline
    seen = set()  # raw-word identities already emitted — guards a word that straddles two
                  # abutting same-clip segments from being double-counted in the transcript
    for seg in cuts.get("segments", []):
        clip = os.path.basename(seg["clip"])
        s, e = float(seg["start"]), float(seg["end"])
        dur = e - s
        if dur <= 0:
            continue
        for w in by_clip.get(clip, []):
            ws, we = w.get("start"), w.get("end")
            if ws is None or we is None:
                continue
            # keep any word overlapping the kept segment; clamp to the segment
            if we <= s or ws >= e:
                continue
            if id(w) in seen:        # already emitted by an abutting segment — don't double-count
                continue
            seen.add(id(w))
            cs, ce = max(ws, s), min(we, e)
            out_words.append({
                "text": str(w.get("w", "")).strip(),
                "start": round(cursor + (cs - s), 3),
                "end": round(cursor + (ce - s), 3),
                "type": "word",
            })
        cursor += dur

    out_words = [w for w in out_words if w["text"]]

    # apply the dictionary to the canonical transcript — once, here, for everyone downstream
    fixes, flags = [], []
    for w in out_words:
        new, note = fix_word(w["text"], auto, flag)
        if note and note[0] == "auto":
            # 2026-09-25: only a CHANGE is a fix — "AI" already spelled "AI" used to print
            # a noisy no-op "auto-fixed: AI→AI". Case-sensitive compare on purpose.
            if new != w["text"]:
                w["text"] = new
                fixes.append((note[1], note[2]))
        elif note and note[0] == "flag":
            flags.append(note[1])

    text = " ".join(w["text"] for w in out_words)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text).strip()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "text": text,
            "language_code": language,
            "engine": "whisperx-large-v3 (remapped from raw cut, no re-transcription)",
            "words": out_words,
        }, f, indent=2)
    print(f"[export-transcript] {len(out_words)} words → {out_path}")
    if fixes:
        uniq = sorted(set(fixes))
        print("[export-transcript] auto-fixed:", ", ".join(f"{a}→{b}" for a, b in uniq))
    if flags:
        print("[export-transcript] ⚠ REVIEW these in context:", ", ".join(sorted(set(flags))))


if __name__ == "__main__":
    main()
