"""Score a crop pack (the files the app ships) on held-out photos of one source, the way the app
decides: temperature + thresholds from the manifest, and the farmer's chosen crop = the photo's
true crop, so a confident answer about ANOTHER crop counts as a "wrong crop" retake.

    python -m eval.field_eval --pack path/to/public/models/crop --data data/crop/test --source plantdoc_field
    python -m eval.field_eval --pack runs/crop --data data/crop/test --source plantdoc_field   (a new run)

Prints and writes <out>.json: accuracy, coverage, accuracy when it answers, how many wrong answers
were caught as "not sure", and per-class numbers. Only quote it with its source name.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.decision import decide, softmax  # noqa: E402


def load_pack(pack: Path):
    """A shipped pack has manifest.json; a fresh training run has pack_params.json."""
    if (pack / "manifest.json").exists():
        m = json.loads((pack / "manifest.json").read_text())
        model, T, th = m["model"], m["temperature"], m["thresholds"]
        mean, std = m["input"].get("mean", [0.5] * 3), m["input"].get("std", [0.5] * 3)
    else:
        m = json.loads((pack / "pack_params.json").read_text())
        model, T, th = m["model_file"], m["temperature"], m["thresholds"]
        mean, std = m["input"]["mean"], m["input"]["std"]
    labels = [l["label"] for l in json.loads((pack / "labels.json").read_text())]
    return pack / model, labels, float(T), th, mean, std


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--data", default="data/crop/test")
    ap.add_argument("--source", default="plantdoc_field")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    import onnxruntime as ort
    from PIL import Image

    model_path, labels, T, th, mean, std = load_pack(Path(a.pack))
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    mean_, std_ = np.array(mean, np.float32)[:, None, None], np.array(std, np.float32)[:, None, None]

    def tf(im):
        """Same as training's Resize(256) + CenterCrop(224) + Normalize, in plain PIL/numpy."""
        w, h = im.size
        s = 256 / min(w, h)
        im = im.resize((max(224, round(w * s)), max(224, round(h * s))), Image.BILINEAR)
        W, H = im.size
        l, t = int(round((W - 224) / 2.0)), int(round((H - 224) / 2.0))
        x = np.asarray(im.crop((l, t, l + 224, t + 224)), np.float32).transpose(2, 0, 1) / 255.0
        return (x - mean_) / std_

    files = sorted(Path(a.data).glob(f"*/{a.source}_*.jpg"))
    if not files:
        sys.exit(f"No {a.source}_*.jpg images under {a.data}. Run crop_prepare first.")
    Z, Y = [], []
    for i in range(0, len(files), 32):
        batch = files[i:i + 32]
        x = np.stack([tf(Image.open(f).convert("RGB")) for f in batch]).astype(np.float32)
        Z.append(sess.run(["logits"], {"input": x})[0])
        Y += [labels.index(f.parent.name) for f in batch]
    Z, Y = np.concatenate(Z), np.array(Y)
    P = softmax(Z, T)
    d = decide(P, th)                       # class index, or -1 = "not sure"
    top = P.argmax(1)
    crop = lambda k: labels[k].split("_")[0]

    outcome = []
    for y, t, dk in zip(Y, top, d):
        if dk == -1:
            outcome.append("not_sure")
        elif crop(dk) != crop(y):
            outcome.append("wrong_crop_retake")   # app asks the farmer to re-pick; no diagnosis given
        elif dk == y:
            outcome.append("correct")
        else:
            outcome.append("wrong_diagnosis")
    oc = Counter(outcome)
    n = len(Y)
    answered = oc["correct"] + oc["wrong_diagnosis"]
    wrong_top1 = (top != Y)

    per_class = defaultdict(lambda: Counter())
    for y, o in zip(Y, outcome):
        per_class[labels[y]][o] += 1

    res = {
        "source": a.source, "pack": str(a.pack), "n_images": int(n),
        "top1_accuracy": float((top == Y).mean()),
        "outcomes": dict(oc),
        "coverage": answered / n,
        "accuracy_when_answering": (oc["correct"] / answered) if answered else None,
        "wrong_answers_caught": float(np.mean([o != "wrong_diagnosis" for o, w in zip(outcome, wrong_top1) if w])) if wrong_top1.any() else None,
        "per_class": {k: dict(v) for k, v in sorted(per_class.items())},
        "note": "Real-scene photos never used for training. The app's wrong-crop rule is applied.",
    }
    out = Path(a.out or f"field_eval_{a.source}.json")
    out.write_text(json.dumps(res, indent=2))

    print(f"\n{a.source}: {n} held-out photos")
    print(f"  top-1 accuracy (any answer)      {res['top1_accuracy']:.1%}")
    print(f"  app gives a diagnosis on          {res['coverage']:.1%}")
    if answered:
        print(f"  ...and is right on                {res['accuracy_when_answering']:.1%}")
    if res["wrong_answers_caught"] is not None:
        print(f"  wrong answers caught (not sure or wrong-crop retake) {res['wrong_answers_caught']:.1%}")
    print(f"  outcomes: {dict(oc)}")
    for k, v in res["per_class"].items():
        tot = sum(v.values())
        print(f"    {k:28s} {tot:4d} photos  correct {v.get('correct', 0) / tot:.0%}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
