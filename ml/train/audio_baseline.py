"""Machine-sound classifier, small-data edition. Runs on a laptop in seconds.

Data layout (one folder per label, one sub-folder per physical machine):
    data/raw/healthy/pump_A/*.wav|m4a|mp3|ogg|webm
    data/raw/healthy/gen_B/...
    data/raw/faulty/pump_C/...
Long recordings are sliced into 5 s windows; every window keeps its machine ID.

Evaluation is leave-one-machine-out: each machine is scored by a model that never
heard it. That is the number you quote. Usage:
    python -m train.audio_baseline --data data/raw --out runs/baseline
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dsp.logmel import load_audio, logmel, quality, windows  # noqa: E402
from eval.decision import choose_thresholds, fit_temperature, report, softmax  # noqa: E402

AUDIO_EXT = {".wav", ".m4a", ".mp3", ".ogg", ".webm", ".aac", ".flac", ".opus", ".3gp", ".amr"}


def scan(root: Path) -> list[dict]:
    items = []
    for label_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for machine_dir in sorted(p for p in label_dir.iterdir() if p.is_dir()):
            for f in sorted(machine_dir.rglob("*")):
                if f.suffix.lower() in AUDIO_EXT:
                    items.append({"path": str(f), "label": label_dir.name, "machine": machine_dir.name})
    return items


def features(lm: np.ndarray) -> np.ndarray:
    """Per-mel-bin mean and std over time of the normalised log-Mel -> 128 numbers.
    Computed identically inside the exported ONNX graph from the [1,1,64,309] input."""
    return np.concatenate([lm.mean(axis=1), lm.std(axis=1)])


def build(items, skip_bad_quality=True):
    X, y, groups, rec, dropped = [], [], [], [], Counter()
    labels = sorted({i["label"] for i in items})
    for r, it in enumerate(items):
        x = load_audio(it["path"])
        for w in windows(x):
            ok, why = quality(w)
            if not ok and skip_bad_quality:
                dropped[why] += 1
                continue
            X.append(features(logmel(w)))
            y.append(labels.index(it["label"]))
            groups.append(it["machine"])
            rec.append(r)
    return np.array(X), np.array(y), np.array(groups), np.array(rec), labels, dropped


def make_model(C=0.5):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000, class_weight="balanced"))


def logits_of(model, X):
    z = model.decision_function(X)
    return np.stack([np.zeros_like(z), z], axis=1) if z.ndim == 1 else z


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw")
    ap.add_argument("--out", default="runs/baseline")
    ap.add_argument("--C", type=float, default=0.5)
    ap.add_argument("--keep-bad-quality", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    items = scan(Path(a.data))
    if not items:
        sys.exit(f"No audio found under {a.data}/<label>/<machine>/")
    t0 = time.time()
    X, y, g, rec, labels, dropped = build(items, not a.keep_bad_quality)
    machines_per_label = {l: sorted({str(gm) for gm, yy in zip(g, y) if yy == i}) for i, l in enumerate(labels)}
    print(f"{len(items)} recordings -> {len(X)} windows from {len(set(g))} machines "
          f"in {time.time() - t0:.1f}s; dropped by quality: {dict(dropped)}")
    for l, ms in machines_per_label.items():
        print(f"  {l}: {len(ms)} machines {ms}")
    if len(labels) < 2:
        sys.exit("Need at least two labels (e.g. healthy and faulty).")
    if len(set(g)) < 3:
        sys.exit("Need at least 3 distinct machines for a held-out evaluation.")

    # ---- leave-one-machine-out -------------------------------------------------
    oof = np.zeros((len(y), len(labels)))
    for tr, te in LeaveOneGroupOut().split(X, y, g):
        if len(set(y[tr])) < len(labels):        # a label vanished from training
            oof[te] = np.log(np.bincount(y[tr], minlength=len(labels)) + 1)  # prior only
            continue
        m = make_model(a.C).fit(X[tr], y[tr])
        oof[te] = logits_of(m, X[te])

    T = fit_temperature(oof, y)
    p = softmax(oof, T)
    pred = p.argmax(axis=1)
    th = choose_thresholds(p, y)
    maj = np.full_like(y, np.bincount(y).argmax())

    # recording-level (average window probabilities) for reference
    rec_ids = np.unique(rec)
    rec_p = np.stack([p[rec == r].mean(axis=0) for r in rec_ids])
    rec_y = np.array([y[rec == r][0] for r in rec_ids])

    per_machine = {}
    for mname in sorted(set(g.tolist())):
        mask = g == mname
        per_machine[mname] = {"label": labels[y[mask][0]], "windows": int(mask.sum()),
                              "accuracy": float((pred[mask] == y[mask]).mean())}

    res = {
        "protocol": "leave-one-machine-out; each machine scored by a model trained without it",
        "unit": "one 5-second window (what the app scores)",
        "labels": labels,
        "counts": {"recordings": len(items), "windows": int(len(y)), "machines": len(set(g)),
                   "machines_per_label": {k: len(v) for k, v in machines_per_label.items()},
                   "windows_per_label": {l: int((y == i).sum()) for i, l in enumerate(labels)},
                   "dropped_by_quality": dict(dropped)},
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "accuracy": float(accuracy_score(y, pred)),
        "majority_class_macro_f1": float(f1_score(y, maj, average="macro")),
        "confusion_matrix": {"rows_true_cols_pred": labels, "matrix": confusion_matrix(y, pred).tolist()},
        "recording_level_macro_f1": float(f1_score(rec_y, rec_p.argmax(1), average="macro")),
        "temperature": T,
        "thresholds": th,
        "decision_layer": report(p, y, th),
        "per_machine": per_machine,
        "caveat": "Temperature and thresholds were fitted on the same out-of-fold predictions "
                  "they are reported on, so the decision-layer numbers are slightly optimistic.",
    }
    (out / "report.json").write_text(json.dumps(res, indent=2))

    # ---- final model on all data, for export ------------------------------------
    final = make_model(a.C).fit(X, y)
    sc, lr = final.named_steps["standardscaler"], final.named_steps["logisticregression"]
    W, b = lr.coef_, lr.intercept_
    if W.shape[0] == 1:  # binary -> 2 logits [0, z]
        W, b = np.vstack([np.zeros_like(W), W]), np.array([0.0, b[0]])
    np.savez(out / "model.npz", mean=sc.mean_, scale=sc.scale_, W=W, b=b,
             labels=np.array(labels), temperature=T)
    (out / "pack_params.json").write_text(json.dumps(
        {"labels": labels, "temperature": T,
         "thresholds": {k: v for k, v in th.items() if k != "note"}}, indent=2))

    print(f"\nHELD-OUT (unseen machines): macro-F1 {res['macro_f1']:.2f}, accuracy {res['accuracy']:.2f} "
          f"on {len(y)} windows / {len(set(g))} machines  (majority-class macro-F1 "
          f"{res['majority_class_macro_f1']:.2f})")
    print("Confusion (rows=true, cols=pred):", labels)
    for l, row in zip(labels, res["confusion_matrix"]["matrix"]):
        print(f"  {l:>10}: {row}")
    dl = res["decision_layer"]
    print(f"Decision layer: coverage {dl['coverage']:.0%}, wrong flagged 'not sure' "
          f"{dl['wrong_flagged_uncertain'] if dl['wrong_flagged_uncertain'] is None else format(dl['wrong_flagged_uncertain'], '.0%')}")
    print("Per machine:", {k: round(v['accuracy'], 2) for k, v in per_machine.items()})
    print(f"Saved {out}/report.json, model.npz, pack_params.json")
    return res


if __name__ == "__main__":
    main()
