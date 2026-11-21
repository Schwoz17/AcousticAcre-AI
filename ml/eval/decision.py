"""Decision layer shared by training, evaluation and (mirrored) the app.

p = softmax(logits / T); DIAGNOSIS if top1>=conf and margin>=margin and entropy<=entropy,
else UNCERTAIN. T and thresholds are written into the pack manifest.
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy.optimize import minimize_scalar


def softmax(z: np.ndarray, T: float = 1.0) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64) / T
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    def nll(logT):
        p = softmax(logits, np.exp(logT))
        return -np.mean(np.log(p[np.arange(len(y)), y] + 1e-12))
    return float(np.exp(minimize_scalar(nll, bounds=(-3, 3), method="bounded").x))


def stats(p: np.ndarray):
    s = np.sort(p, axis=1)[:, ::-1]
    top1 = s[:, 0]
    margin = s[:, 0] - (s[:, 1] if p.shape[1] > 1 else 0)
    ent = -(p * np.log(p + 1e-12)).sum(axis=1)
    return top1, margin, ent


def decide(p: np.ndarray, th: dict) -> np.ndarray:
    """Returns predicted class, or -1 for UNCERTAIN."""
    top1, margin, ent = stats(p)
    ok = (top1 >= th["conf"]) & (margin >= th["margin"]) & (ent <= th["entropy"])
    return np.where(ok, p.argmax(axis=1), -1)


def choose_thresholds(p: np.ndarray, y: np.ndarray, min_flagged_wrong: float = 0.6) -> dict:
    """Max coverage subject to flagging >= min_flagged_wrong of wrong predictions."""
    n_cls = p.shape[1]
    wrong = p.argmax(axis=1) != y
    default = {"conf": 0.70, "margin": 0.20, "entropy": float(np.log(n_cls))}
    if wrong.sum() == 0:
        return {**default, "note": "no wrong predictions on calibration data; spec defaults used"}
    best = None
    for conf, margin, ent in itertools.product(np.arange(0.5, 0.99, 0.025), np.arange(0, 0.6, 0.05),
                                               np.linspace(0.1, np.log(n_cls), 12)):
        th = {"conf": float(conf), "margin": float(margin), "entropy": float(ent)}
        d = decide(p, th)
        flagged_wrong = np.mean(d[wrong] == -1)
        coverage = np.mean(d != -1)
        if flagged_wrong >= min_flagged_wrong and (best is None or coverage > best[0]):
            best = (coverage, th)
    return best[1] if best else {**default, "note": "target unreachable; spec defaults used"}


def report(p: np.ndarray, y: np.ndarray, th: dict) -> dict:
    d = decide(p, th)
    wrong = p.argmax(axis=1) != y
    cov = d != -1
    return {
        "coverage": float(cov.mean()),
        "accuracy_when_confident": float((d[cov] == y[cov]).mean()) if cov.any() else None,
        "wrong_flagged_uncertain": float((d[wrong] == -1).mean()) if wrong.any() else None,
        "n": int(len(y)),
    }
