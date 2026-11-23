"""Fair before/after test for the pump model when new machines are added.

BEFORE: train on the ORIGINAL machines only (what the app ships today), score each NEW machine.
AFTER:  leave-one-machine-out over ALL machines; report the same NEW machines, each scored by a
        model trained on every other machine (never on itself).
Both numbers are on the same unseen machines, so they can be compared directly.

    python -m eval.machine_compare --data data/raw --original pump_id_00,pump_id_02,pump_id_04,pump_id_06
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train.audio_baseline import build, logits_of, make_model, scan  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw")
    ap.add_argument("--original", default="pump_id_00,pump_id_02,pump_id_04,pump_id_06")
    ap.add_argument("--C", type=float, default=0.5)
    ap.add_argument("--out", default="machine_compare.json")
    a = ap.parse_args(argv)

    items = scan(Path(a.data))
    X, y, g, _rec, labels, dropped = build(items)
    orig = set(a.original.split(","))
    machines = sorted(set(g.tolist()))
    new = [m for m in machines if m not in orig]
    if not new or not (orig & set(machines)):
        sys.exit(f"Need both original and new machines. Found: {machines}")
    print(f"{len(machines)} machines ({len(orig & set(machines))} original, {len(new)} new), {len(y)} windows")

    is_orig = np.isin(g, list(orig))
    before_model = make_model(a.C).fit(X[is_orig], y[is_orig])
    pred_before = np.full_like(y, -1)
    pred_after = np.full_like(y, -1)
    for m in machines:
        te = g == m
        if m in new:
            pred_before[te] = logits_of(before_model, X[te]).argmax(1)
        tr = ~te
        pred_after[te] = logits_of(make_model(a.C).fit(X[tr], y[tr]), X[te]).argmax(1)

    on_new = np.isin(g, new)
    per = {}
    for m in new:
        k = g == m
        per[m] = {"before_accuracy": float((pred_before[k] == y[k]).mean()),
                  "after_accuracy": float((pred_after[k] == y[k]).mean()), "windows": int(k.sum())}
    res = {
        "labels": labels, "original_machines": sorted(orig & set(machines)), "new_machines": new,
        "before_macro_f1_on_new_machines": float(f1_score(y[on_new], pred_before[on_new], average="macro")),
        "after_macro_f1_on_new_machines": float(f1_score(y[on_new], pred_after[on_new], average="macro")),
        "after_macro_f1_all_machines_lomo": float(f1_score(y, pred_after, average="macro")),
        "chance_macro_f1_majority": float(f1_score(y[on_new], np.full(on_new.sum(), np.bincount(y[on_new]).argmax()), average="macro")),
        "per_new_machine": per, "dropped_by_quality": dict(dropped),
        "note": "Same unseen machines in both numbers. MIMII/DCASE data are CC BY-NC-SA 4.0 (non-commercial).",
    }
    Path(a.out).write_text(json.dumps(res, indent=2))
    print(f"\nOn the {len(new)} NEW machines (never heard in training):")
    print(f"  BEFORE (trained on original {len(orig & set(machines))}): macro-F1 {res['before_macro_f1_on_new_machines']:.2f}")
    print(f"  AFTER  (trained on all others):        macro-F1 {res['after_macro_f1_on_new_machines']:.2f}")
    print(f"  (always-guess-one-label baseline:       {res['chance_macro_f1_majority']:.2f})")
    print(f"All {len(machines)} machines, leave-one-machine-out: macro-F1 {res['after_macro_f1_all_machines_lomo']:.2f}")
    for m, v in per.items():
        print(f"    {m:16s} before {v['before_accuracy']:.0%}  after {v['after_accuracy']:.0%}  ({v['windows']} windows)")
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()
