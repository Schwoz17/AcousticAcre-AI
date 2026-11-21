"""Download public leaf datasets via TensorFlow Datasets (preinstalled on Colab) and write
an image folder in our diagnosis-ID classes.

  cassava       field photos (Uganda), own train/validation/test splits  -> FIELD test set
  plant_village lab photos (plain background), random split              -> LAB test set (not field accuracy)

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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/crop")
    ap.add_argument("--max-per-class", type=int, default=1500, help="per split-source-class cap (train)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-plantvillage", action="store_true")
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

    (out / "sources.json").write_text(json.dumps({
        "cassava_field": "TFDS 'cassava' (iCassava 2019, field photos, Uganda); official splits",
        "plantvillage_lab": "TFDS 'plant_village' (lab photos, plain background); random image split. "
                            "Test accuracy here is NOT field accuracy.",
        "counts": {f"{s}/{src}": dict(c) for (s, src), c in counts.items()},
    }, indent=2))
    print("done ->", out)


if __name__ == "__main__":
    main()
