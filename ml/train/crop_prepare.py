"""Download public leaf datasets via TensorFlow Datasets (preinstalled on Colab) and write
an image folder in our diagnosis-ID classes.

  cassava       field photos (Uganda), own train/validation/test splits  -> FIELD test set
  plant_village lab photos (plain background), random split              -> LAB test set (not field accuracy)
  plantdoc      web-collected real-scene photos (maize, tomato), deduplicated,
                stratified 55/15/30 split                                -> FIELD test set for maize/tomato

    python -m train.crop_prepare --out data/crop --max-per-class 1500

Output: data/crop/{train,val,test}/<diagnosis_id>/<source>_<n>.jpg  + data/crop/sources.json
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

CASSAVA = {"cbb": "cassava_bacterial_blight", "cbsd": "cassava_brown_streak", "cgm": "cassava_green_mite",
           "cmd": "cassava_mosaic", "healthy": "cassava_healthy"}


def map_plantvillage(name: str) -> str | None:
    """PlantVillage label name -> our diagnosis ID (None = not used)."""
    n = name.lower()
    if n.startswith("corn"):
        if "common_rust" in n:
            return "maize_common_rust"
        if "northern_leaf_blight" in n:
            return "maize_northern_leaf_blight"
        if "cercospora" in n or "gray_leaf_spot" in n:
            return "maize_gray_leaf_spot"
        if "healthy" in n:
            return "maize_healthy"
        return None
    if n.startswith("tomato"):
        if "early_blight" in n:
            return "tomato_early_blight"
        if "late_blight" in n:
            return "tomato_late_blight"
        if "yellow_leaf_curl" in n:
            return "tomato_yellow_leaf_curl"
        if "healthy" in n:
            return "tomato_healthy"
        return "tomato_other_leaf_problem"   # bacterial spot, leaf mold, septoria, mites, target spot, mosaic
    return None


PLANTDOC = {
    "Corn Gray leaf spot": "maize_gray_leaf_spot",
    "Corn leaf blight": "maize_northern_leaf_blight",
    "Corn rust leaf": "maize_common_rust",
    "Tomato Early blight leaf": "tomato_early_blight",
    "Tomato leaf": "tomato_healthy",
    "Tomato leaf late blight": "tomato_late_blight",
    "Tomato leaf yellow virus": "tomato_yellow_leaf_curl",
    "Tomato Septoria leaf spot": "tomato_other_leaf_problem",
    "Tomato leaf bacterial spot": "tomato_other_leaf_problem",
    "Tomato leaf mosaic virus": "tomato_other_leaf_problem",
    "Tomato mold leaf": "tomato_other_leaf_problem",
    "Tomato two spotted spider mites leaf": "tomato_other_leaf_problem",
}


PLANTDOC_NOTE = ("PlantDoc (Singh et al. 2019, CC BY-SA 4.0), web-collected real-scene maize and tomato photos, "
                 "near-duplicates removed before a stratified 55/15/30 split. Quotable as a real-scene result "
                 "for maize/tomato, with the caveat that the photos are not from Nigerian farms.")


def ahash(img, n=8):
    """Tiny perceptual hash: catches the same photo re-uploaded at another size."""
    g = img.convert("L").resize((n, n))
    px = list(g.getdata())
    m = sum(px) / len(px)
    return sum(1 << i for i, v in enumerate(px) if v > m) & 0xFFFFFFFFFFFFFFFF


def add_plantdoc(out, save, rnd, fractions=(0.55, 0.15, 0.30)):
    """PlantDoc (Singh et al. 2019, CC BY-SA 4.0) from the Hugging Face mirror.
    Duplicates are removed BEFORE splitting so one photo never lands in train and test."""
    from datasets import load_dataset
    import numpy as np
    from PIL import Image
    # PlantDoc was collected from the web, so some photos may be PlantVillage images.
    # Hash every maize/tomato lab photo already written and drop PlantDoc matches (no leakage).
    lab = []
    for f in Path(out).glob("*/*/plantvillage_lab_*.jpg"):
        if f.parent.name.startswith(("maize_", "tomato_")):
            with Image.open(f) as im:
                lab.append(ahash(im))
    print(f"plantdoc: checking against {len(lab)} lab photos for overlap")
    seen = np.array(lab, dtype=np.uint64)

    def near_dup(h, max_bits=3):  # reads the current 'seen' from the enclosing scope
        """True if h is within max_bits differing bits of any hash seen so far."""
        if seen.size == 0:
            return False
        x = np.bitwise_xor(seen, np.uint64(h)).view(np.uint8)
        return bool((np.unpackbits(x).reshape(-1, 64).sum(1) <= max_bits).any())
    ds = load_dataset("Project-AgML/plant_doc_classification", split="train")
    names = ds.features["label"].names
    by_class, dupes = defaultdict(list), 0
    for i, ex in enumerate(ds):
        diag = PLANTDOC.get(names[ex["label"]])
        if not diag:
            continue
        img = ex["image"].convert("RGB")
        h = ahash(img)
        if near_dup(h):
            dupes += 1
            continue
        seen = np.append(seen, np.uint64(h))
        by_class[diag].append((i, img))
    for diag, items in sorted(by_class.items()):
        rnd.shuffle(items)
        n = len(items)
        a, b = int(n * fractions[0]), int(n * (fractions[0] + fractions[1]))
        for split, part in (("train", items[:a]), ("val", items[a:b]), ("test", items[b:])):
            for i, img in part:
                save(split, diag, "plantdoc_field", np.asarray(img), i)
    print(f"plantdoc: {sum(len(v) for v in by_class.values())} images kept, {dupes} duplicates dropped")
    return dupes


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/crop")
    ap.add_argument("--max-per-class", type=int, default=1500, help="per split-source-class cap (train)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-plantvillage", action="store_true")
    ap.add_argument("--skip-plantdoc", action="store_true")
    ap.add_argument("--only-plantdoc", action="store_true", help="add PlantDoc to an existing data folder")
    a = ap.parse_args(argv)

    import tensorflow_datasets as tfds
    from PIL import Image

    out = Path(a.out)
    rnd = random.Random(a.seed)
    counts: dict = defaultdict(Counter)
    caps = {"train": a.max_per_class, "val": max(150, a.max_per_class // 5), "test": max(150, a.max_per_class // 5)}

    def save(split, diag, source, img, i):
        if counts[(split, source)][diag] >= caps[split]:
            return
        d = out / split / diag
        d.mkdir(parents=True, exist_ok=True)
        im = Image.fromarray(img)
        im.thumbnail((384, 384))                       # keep files small; training crops to 224
        im.save(d / f"{source}_{i:06d}.jpg", quality=90)
        counts[(split, source)][diag] += 1

    if a.only_plantdoc:
        add_plantdoc(out, save, rnd)
        for s_ in ("train", "val", "test"):
            print("plantdoc", s_, dict(counts[(s_, "plantdoc_field")]))
        src = out / "sources.json"
        meta = json.loads(src.read_text()) if src.exists() else {}
        meta["plantdoc_field"] = PLANTDOC_NOTE
        meta.setdefault("counts", {}).update({f"{s_}/plantdoc_field": dict(counts[(s_, "plantdoc_field")]) for s_ in ("train", "val", "test")})
        src.write_text(json.dumps(meta, indent=2))
        return

    # --- cassava: field photos, official splits ---------------------------------
    ds, info = tfds.load("cassava", with_info=True)
    names = info.features["label"].names
    for tf_split, ours in [("train", "train"), ("validation", "val"), ("test", "test")]:
        for i, ex in enumerate(tfds.as_numpy(ds[tf_split])):
            diag = CASSAVA.get(names[int(ex["label"])])
            if diag:
                save(ours, diag, "cassava_field", ex["image"], i)
        print("cassava", tf_split, dict(counts[(ours, "cassava_field")]))

    # --- PlantVillage: lab photos, random 80/10/10 ------------------------------
    if not a.skip_plantvillage:
        ds, info = tfds.load("plant_village", with_info=True, split="train")
        names = info.features["label"].names
        for i, ex in enumerate(tfds.as_numpy(ds)):
            diag = map_plantvillage(names[int(ex["label"])])
            if not diag:
                continue
            r = rnd.random()
            split = "train" if r < 0.8 else "val" if r < 0.9 else "test"
            save(split, diag, "plantvillage_lab", ex["image"], i)
        for s in ("train", "val", "test"):
            print("plantvillage", s, dict(counts[(s, "plantvillage_lab")]))

    if not a.skip_plantdoc:
        add_plantdoc(out, save, rnd)
        for s_ in ("train", "val", "test"):
            print("plantdoc", s_, dict(counts[(s_, "plantdoc_field")]))

    (out / "sources.json").write_text(json.dumps({
        "cassava_field": "TFDS 'cassava' (iCassava 2019, field photos, Uganda); official splits",
        "plantvillage_lab": "TFDS 'plant_village' (lab photos, plain background); random image split. "
                            "Test accuracy here is NOT field accuracy.",
        "plantdoc_field": PLANTDOC_NOTE,
        "counts": {f"{s}/{src}": dict(c) for (s, src), c in counts.items()},
    }, indent=2))
    print("done ->", out)


if __name__ == "__main__":
    main()
