#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["mediapipe>=0.10", "opencv-python-headless", "numpy"]
# ///
"""cutout.py — the person cut-out for the "escena detrás de él" move (reference-craft.md § 2.6).

Segments the speaker out of a clip with MediaPipe's selfie segmenter and writes a ProRes 4444
STRAIGHT-alpha .mov of just the person, so a bed (an assets/motion/elements loop, an artifact, a
prop rain) can play BEHIND them on the track below. Universal: the output is a normal alpha
overlay on every lane (Premiere: bed on V3, cut-out on V4, V1 footage still underneath).

  uv run workflows/cutout.py <clip> --from 3.70 --to 6.00 --out projects/<job>/hf-graphics/cutout/renders/cutout-sinpagar.mov
  uv run workflows/cutout.py <clip> --from 3.70 --to 6.00 --out ... --size 1080x1920   # conform to the sequence
  uv run workflows/cutout.py <clip> --from 3.70 --to 6.00 --out ... --preview          # also writes <out>.png (mid frame over magenta)

Locked from example-reel (2026-09-14, the first shipped cut-out): temporal smoothing 0.7·prev +
0.3·cur on the confidence mask (kills the breathing edge), Gaussian blur σ 1.2 on the mask (the
hair line), threshold-free (the soft mask IS the alpha). ~2 s of 1080x1920 footage ≈ 30 s of
processing. Rotation metadata is honoured (iPhone clips carry -90°), so the output is upright.

The model (selfie_segmenter.tflite, ~250 KB, Apache-2.0) is fetched once into assets/models/.
"""
import argparse, json, os, subprocess, sys, urllib.request
import numpy as np

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "assets", "models", "selfie_segmenter.tflite")
SMOOTH_PREV, SMOOTH_CUR, BLUR_SIGMA = 0.7, 0.3, 1.2


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    w, h = int(j["width"]), int(j["height"])
    rot = 0
    for sd in j.get("side_data_list", []):
        if "rotation" in sd: rot = int(sd["rotation"])
    if abs(rot) == 90: w, h = h, w                     # ffmpeg autorotates on decode; dims swap
    num, den = j["r_frame_rate"].split("/")
    return w, h, f"{num}/{den}", int(num) / int(den)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip"); ap.add_argument("--from", dest="t0", type=float, required=True); ap.add_argument("--to", dest="t1", type=float, required=True)
    ap.add_argument("--out", required=True, help="ProRes 4444 .mov (straight alpha)")
    ap.add_argument("--size", help="WxH to conform the output to (default: the clip's upright size)")
    ap.add_argument("--model", default=MODEL); ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.model):
        os.makedirs(os.path.dirname(a.model), exist_ok=True)
        print(f"fetching selfie_segmenter.tflite → {a.model}", file=sys.stderr)
        urllib.request.urlretrieve(MODEL_URL, a.model)

    import cv2, mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision

    w, h, fps_str, fps = probe(a.clip)
    if a.size: ow, oh = map(int, a.size.lower().split("x"))
    else: ow, oh = w, h
    dur = a.t1 - a.t0
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a.t0:.4f}", "-i", a.clip, "-t", f"{dur:.4f}",
                            "-vf", f"scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{ow}x{oh}", "-r", fps_str, "-i", "-",
                            "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", a.out], stdin=subprocess.PIPE)
    opts = vision.ImageSegmenterOptions(base_options=mpp.BaseOptions(model_asset_path=a.model), running_mode=vision.RunningMode.VIDEO,
                                        output_category_mask=False, output_confidence_masks=True)
    n = 0; prev = None; polarity = None; mid = None; nbytes = ow * oh * 3
    with vision.ImageSegmenter.create_from_options(opts) as seg:
        while True:
            buf = dec.stdout.read(nbytes)
            if len(buf) < nbytes: break
            rgb = np.frombuffer(buf, np.uint8).reshape(oh, ow, 3)
            res = seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(round(n * 1000.0 / fps)))
            masks = res.confidence_masks
            m = masks[1].numpy_view() if len(masks) > 1 else masks[0].numpy_view()
            m = m.astype(np.float32)
            if polarity is None:                        # the person sits bottom-centre; the corners are room
                centre = m[int(oh * 0.55):int(oh * 0.95), int(ow * 0.3):int(ow * 0.7)].mean()
                corners = (m[:oh // 8, :ow // 8].mean() + m[:oh // 8, -ow // 8:].mean()) / 2
                # invert only when the corners are CLEARLY the lit side; an empty mask (no person in
                # frame, e.g. a screen-recording clip) stays as is and renders transparent, which is right
                polarity = -1 if corners > centre + 0.2 else 1
                if centre < 0.05 and corners < 0.05:
                    print(f"⚠ no person found on the first frame (centre={centre:.2f}, corners={corners:.2f}) — is this a talking-head clip?", file=sys.stderr)
                print(f"mask polarity: {'person=1' if polarity == 1 else 'inverted (person=0)'}  centre={centre:.2f} corners={corners:.2f}", file=sys.stderr)
            if polarity < 0: m = 1.0 - m
            m = m if prev is None else SMOOTH_PREV * prev + SMOOTH_CUR * m
            prev = m
            alpha = cv2.GaussianBlur(m, (0, 0), BLUR_SIGMA)
            rgba = np.dstack([rgb, np.clip(alpha * 255.0, 0, 255).astype(np.uint8)])
            enc.stdin.write(rgba.tobytes())
            if a.preview and n == int(dur * fps / 2): mid = rgba.copy()
            n += 1
    enc.stdin.close(); enc.wait(); dec.wait()
    if a.preview and mid is not None:
        bg = np.zeros_like(mid[:, :, :3]); bg[:, :] = (255, 0, 255)
        al = mid[:, :, 3:4].astype(np.float32) / 255.0
        comp = (mid[:, :, :3].astype(np.float32) * al + bg * (1 - al)).astype(np.uint8)
        cv2.imwrite(a.out + ".png", cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))
    print(f"-> {a.out}  {n} frames @ {fps_str}  {ow}x{oh}  ProRes 4444 straight alpha")


if __name__ == "__main__":
    main()
