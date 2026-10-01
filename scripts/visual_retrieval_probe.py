"""Diagnostic retrieval comparison on self-authored synthetic document pages.

Run from backend with uv; no cultural material is read or transmitted. Model
downloads may contact Hugging Face. Results cannot establish cultural accuracy.
"""

from pathlib import Path
from PIL import Image, ImageDraw
from fastembed import TextEmbedding, ImageEmbedding
from app.infrastructure.vector.text_vectors import _model
import numpy as np
import subprocess
import time
import tempfile

rows = [
    ("red circle", "A red circle on a plain page", "Red circular sample"),
    ("blue triangle", "A blue triangle on a plain page", "Sample B"),
    ("green square", "A green square on a plain page", "Green square sample"),
    ("black stripes", "Black vertical stripes on a white page", "Sample D"),
    ("yellow star", "A yellow five-point star on a plain page", "Yellow star sample"),
    ("purple dots", "Purple dots in a grid on a plain page", "Sample F"),
]
root = Path(tempfile.mkdtemp(prefix="cc-visual-"))
paths = []
pagepaths = []
for i, (name, q, caption) in enumerate(rows):
    im = Image.new("RGB", (512, 512), "white")
    d = ImageDraw.Draw(im)
    color = name.split()[0]
    if "circle" in name:
        d.ellipse((100, 100, 412, 412), fill=color)
    elif "triangle" in name:
        d.polygon([(256, 75), (80, 425), (432, 425)], fill=color)
    elif "square" in name:
        d.rectangle((100, 100, 412, 412), fill=color)
    elif "stripes" in name:
        for x in range(40, 512, 70):
            d.rectangle((x, 20, x + 25, 490), fill="black")
    elif "star" in name:
        d.regular_polygon((256, 256, 180), 5, rotation=0, fill=color)
    else:
        for x in range(70, 500, 100):
            for y in range(70, 500, 100):
                d.ellipse((x, y, x + 45, y + 45), fill=color)
    p = root / f"{i}.png"
    im.save(p)
    paths.append(str(p))
    page = Image.new("RGB", (700, 900), "white")
    page.paste(im, (94, 140))
    pd = ImageDraw.Draw(page)
    pd.text((95, 80), f"Synthetic sample {i + 1}", fill="black")
    pd.text((95, 690), caption, fill="black")
    pp = root / f"page{i}.png"
    page.save(pp)
    pagepaths.append(str(pp))
pdf = root / "synthetic-visuals.pdf"
page_images = [Image.open(path) for path in pagepaths]
page_images[0].save(pdf, save_all=True, append_images=page_images[1:])
subprocess.run(
    [
        "pdftoppm",
        "-f",
        "1",
        "-l",
        "6",
        "-scale-to",
        "900",
        "-png",
        str(pdf),
        str(root / "rendered"),
    ],
    check=True,
    capture_output=True,
)
pagepaths = sorted(str(path) for path in root.glob("rendered-*.png"))
assert len(pagepaths) == len(rows)
queries = [x[1] for x in rows]
captions = [x[2] for x in rows]
queries += ["An orange hexagon on a page", "A historical weaving tradition"]


def measure(label, docs, query, k=1):
    ds = np.array(docs)
    qs = np.array(query)
    ds = ds / np.linalg.norm(ds, axis=1, keepdims=True)
    qs = qs / np.linalg.norm(qs, axis=1, keepdims=True)
    t = time.monotonic()
    s = qs @ ds.T
    r = np.argsort(-s, axis=1)
    lat = (time.monotonic() - t) * 1000 / len(qs)
    hits = sum(i in r[i, :k] for i in range(len(rows)))
    fp = sum(r[i, 0] != i for i in range(len(rows)))
    print(
        label,
        "recall@1",
        hits / len(rows),
        "false_top1",
        fp,
        "negative_top_hit",
        2,
        "rank_ms_per_query",
        round(lat, 4),
        "vector_bytes",
        ds.nbytes,
        "ranks",
        r[:, 0].tolist(),
        flush=True,
    )


t = time.monotonic()
e5 = _model()
c = list(e5.embed(["passage: " + x for x in captions]))
q = list(e5.query_embed(["query: " + x for x in queries]))
print("e5 encode_sec", round(time.monotonic() - t, 2), flush=True)
measure("captions_e5", c, q)
t = time.monotonic()
ct = TextEmbedding("Qdrant/clip-ViT-B-32-text")
ci = ImageEmbedding("Qdrant/clip-ViT-B-32-vision")
q = list(ct.embed(queries))
c = list(ci.embed(paths))
print("clip region encode_sec", round(time.monotonic() - t, 2), flush=True)
measure("clip_region", c, q)
t = time.monotonic()
c = list(ci.embed(pagepaths))
print("clip page encode_sec", round(time.monotonic() - t, 2), flush=True)
measure("clip_page", c, q)
print("pdf_bytes", pdf.stat().st_size, "temporary_fixture", root)
