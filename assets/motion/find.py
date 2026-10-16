#!/usr/bin/env python3
"""find.py — search the motion library by concept (icons + elements + illustrations), accent-insensitive.
  python3 assets/motion/find.py dinero            → every icon/element whose slug, name or keywords match
  python3 assets/motion/find.py cliente feliz     → rows matching ALL words
  python3 assets/motion/find.py --elements globo  → elements only  (--icons / --illustrations likewise)
Prints slug · duration · the ready-to-use paths (on-dark/on-light webm for icons, the mp4 for elements, the png for illustrations)."""
import json, os, sys, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
def fold(s): return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
args = [a for a in sys.argv[1:] if not a.startswith("--")]; flags = [a for a in sys.argv[1:] if a.startswith("--")]
if not args: print(__doc__); sys.exit(0)
words = [fold(a) for a in args]
def hit(*fields): 
    blob = fold(" ".join(f for f in fields if f)); return all(w in blob for w in words)
only = [f for f in flags if f in ("--icons","--elements","--illustrations")]
if not only or "--icons" in only:
    cat = json.load(open(f"{HERE}/icons/catalog.json"))
    rows = [c for c in cat if hit(c["slug"], c["name_es"], c["keywords"])]
    if rows:
        print(f"ICONS ({len(rows)})")
        for c in rows: print(f"  {c['slug']:34s} {c['duration']:4.1f}s {c['fps']:>5}  icons/on-dark/{c['slug']}.webm · icons/on-light/{c['slug']}.webm")
if not only or "--elements" in only:
    cat = json.load(open(f"{HERE}/elements/catalog.json"))
    rows = [c for c in cat if hit(c["id"], c["file"], c["desc_es"], c["keywords"])]
    if rows:
        print(f"ELEMENTS ({len(rows)})")
        for c in rows: print(f"  {c['id']:6s} {c['file']:36s} {c['duration']:4.1f}s loop={'yes' if c['seamless_loop'] else 'no '} cov={c['coverage']:6s} — {c['desc_es']}")
if not only or "--illustrations" in only:
    cat = json.load(open(f"{HERE}/illustrations/catalog.json"))
    rows = [c for c in cat if hit(c["slug"], c["name_es"], c["keywords"])]
    if rows:
        print(f"ILLUSTRATIONS ({len(rows)})")
        for c in rows: print(f"  {c['slug']:30s} {c['size']:>10s}  illustrations/{c['slug']}.png — {c['name_es']}")
