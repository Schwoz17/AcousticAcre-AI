"""Crop disease classifier: EfficientNet-Lite0 fine-tune, calibration, evaluation, ONNX export.
Run on a Colab GPU (Runtime -> Change runtime type -> T4 GPU).

    pip install timm onnx onnxruntime
    python -m train.crop_train --data data/crop --out runs/crop --epochs 8

Outputs in runs/crop/:
    model.onnx            input "input" [N,3,224,224]; outputs "logits" [N,K], "cam" [N,K,7,7]
    model.int8.onnx       (if --quantize and accuracy drop <= 1 point)
    labels.json, pack_params.json (temperature, thresholds, mean/std), report.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.decision import choose_thresholds, fit_temperature, report, softmax  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/crop")
    ap.add_argument("--out", default="runs/crop")
    ap.add_argument("--arch", default="tf_efficientnet_lite0")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--head-epochs", type=int, default=1)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--quantize", action="store_true")
    a = ap.parse_args(argv)

    import timm
    import torch
    import torch.nn as nn
    from sklearn.metrics import confusion_matrix, f1_score
    from torch.utils.data import DataLoader
    from torchvision import datasets, transforms as T

    torch.manual_seed(0)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cpu":
        print("WARNING: no GPU. Runtime -> Change runtime type -> T4 GPU. CPU training is very slow.")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    model = timm.create_model(a.arch, pretrained=True)
    cfg = timm.data.resolve_data_config({}, model=model)
    mean, std = list(cfg["mean"]), list(cfg["std"])
    norm = T.Normalize(mean, std)
    tf_train = T.Compose([
        T.RandomResizedCrop(224, scale=(0.5, 1.0)), T.RandomHorizontalFlip(), T.RandomVerticalFlip(),
        T.ColorJitter(0.4, 0.4, 0.3, 0.03), T.RandomApply([T.GaussianBlur(5, (0.1, 2.0))], p=0.3),
        T.ToTensor(), norm, T.RandomErasing(p=0.25)])
    tf_eval = T.Compose([T.Resize(256), T.CenterCrop(224), T.ToTensor(), norm])

    root = Path(a.data)
    tr = datasets.ImageFolder(root / "train", tf_train)
    va = datasets.ImageFolder(root / "val", tf_eval)
    te = datasets.ImageFolder(root / "test", tf_eval)
    assert tr.classes == va.classes == te.classes, "train/val/test class folders differ"
    labels = tr.classes
    K = len(labels)
    print(f"{K} classes, train {len(tr)}, val {len(va)}, test {len(te)}")
    model.reset_classifier(K)
    model.to(dev)

    # balanced sampling: PlantVillage and cassava classes are very unequal
    counts = np.bincount(tr.targets, minlength=K)
    w = (1.0 / counts)[tr.targets]
    sampler = torch.utils.data.WeightedRandomSampler(torch.tensor(w, dtype=torch.double), len(tr))
    dl_tr = DataLoader(tr, a.bs, sampler=sampler, num_workers=a.workers, pin_memory=True, drop_last=True)
    dl_va = DataLoader(va, a.bs, num_workers=a.workers)
    dl_te = DataLoader(te, a.bs, num_workers=a.workers)

    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler = torch.amp.GradScaler(enabled=dev == "cuda")

    def run_epoch(opt, sched=None):
        model.train()
        t0, tot, n = time.time(), 0.0, 0
        for x, y in dl_tr:
            x, y = x.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
            with torch.autocast(dev, enabled=dev == "cuda"):
                loss = loss_fn(model(x), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            if sched:
                sched.step()
            tot, n = tot + loss.item() * len(y), n + len(y)
        return tot / n, time.time() - t0

    @torch.no_grad()
    def predict(dl):
        model.eval()
        Z, Y = [], []
        for x, y in dl:
            with torch.autocast(dev, enabled=dev == "cuda"):
                Z.append(model(x.to(dev)).float().cpu())
            Y.append(y)
        return torch.cat(Z).numpy(), torch.cat(Y).numpy()

    # stage 1: head only
    for p in model.parameters():
        p.requires_grad = False
    for p in model.get_classifier().parameters():
        p.requires_grad = True
    opt = torch.optim.AdamW(model.get_classifier().parameters(), lr=1e-3, weight_decay=1e-4)
    for e in range(a.head_epochs):
        l, s = run_epoch(opt)
        print(f"head epoch {e + 1}: loss {l:.3f} ({s:.0f}s)")

    # stage 2: full fine-tune, cosine
    for p in model.parameters():
        p.requires_grad = True
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-4, total_steps=a.epochs * len(dl_tr), pct_start=0.15)
    best, best_state = -1.0, None
    for e in range(a.epochs):
        l, s = run_epoch(opt, sched)
        zv, yv = predict(dl_va)
        f1 = f1_score(yv, zv.argmax(1), average="macro")
        print(f"epoch {e + 1}/{a.epochs}: loss {l:.3f}, val macro-F1 {f1:.3f} ({s:.0f}s)")
        if f1 > best:
            best, best_state = f1, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)

    # calibration on val, evaluation on frozen test, reported PER SOURCE
    zv, yv = predict(dl_va)
    Tmp = fit_temperature(zv, yv)
    th = choose_thresholds(softmax(zv, Tmp), yv)
    zt, yt = predict(dl_te)
    pt = softmax(zt, Tmp)
    src = np.array([Path(p).name.rsplit("_", 1)[0] for p, _ in te.samples])

    def block(mask):
        y, p = yt[mask], pt[mask]
        present = sorted(set(y.tolist()))
        return {"n_images": int(mask.sum()),
                "accuracy": float((p.argmax(1) == y).mean()),
                "macro_f1": float(f1_score(y, p.argmax(1), labels=present, average="macro")),
                "classes": [labels[i] for i in present],
                "confusion_matrix": confusion_matrix(y, p.argmax(1), labels=present).tolist(),
                "decision_layer": report(p, y, th)}

    res = {"arch": a.arch, "labels": labels, "temperature": Tmp, "thresholds": th,
           "val_macro_f1_best": best, "by_source": {s: block(src == s) for s in sorted(set(src))},
           "note": "cassava_field = field photos (quotable as field-condition result). "
                   "plantvillage_lab = lab photos with plain backgrounds; do NOT present as field accuracy."}
    (out / "report.json").write_text(json.dumps(res, indent=2))
    for s, b in res["by_source"].items():
        print(f"TEST {s}: accuracy {b['accuracy']:.3f}, macro-F1 {b['macro_f1']:.3f} on {b['n_images']} images; "
              f"coverage {b['decision_layer']['coverage']:.0%}")

    # ---- ONNX export: logits + class activation maps -------------------------------
    class Export(nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m
            self.register_buffer("W", m.get_classifier().weight.detach().clone())  # [K, C]

        def forward(self, x):
            f = self.m.forward_features(x)                 # [N, C, 7, 7]
            logits = self.m.forward_head(f)
            cam = torch.einsum("kc,nchw->nkhw", self.W, f)  # where the model looked, per class
            return logits, cam

    model.eval().cpu()
    exp = Export(model).eval()
    dummy = torch.randn(1, 3, 224, 224)
    onnx_path = out / "model.onnx"
    kw = dict(input_names=["input"], output_names=["logits", "cam"],
              dynamic_axes={"input": {0: "N"}, "logits": {0: "N"}, "cam": {0: "N"}}, opset_version=17)
    try:
        torch.onnx.export(exp, dummy, str(onnx_path), dynamo=False, **kw)
    except TypeError:  # older torch without the dynamo flag
        torch.onnx.export(exp, dummy, str(onnx_path), **kw)

    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        want = exp(dummy)[0].numpy()
    got = sess.run(["logits"], {"input": dummy.numpy()})[0]
    print(f"ONNX check: max |diff| {np.abs(got - want).max():.2e}; size {onnx_path.stat().st_size / 1e6:.1f} MB")

    model_file = "model.onnx"
    if a.quantize:
        model_file = try_quantize(onnx_path, out, va, te, sess, labels) or model_file

    (out / "labels.json").write_text(json.dumps([{"index": i, "label": l, "diagnosis_id": l}
                                                 for i, l in enumerate(labels)], indent=2))
    (out / "pack_params.json").write_text(json.dumps({
        "labels": labels, "temperature": Tmp, "model_file": model_file,
        "thresholds": {k: v for k, v in th.items() if k != "note"},
        "input": {"size": [224, 224], "resize_short_side": 256, "mean": mean, "std": std}}, indent=2))
    print("Saved", out)


def try_quantize(fp32_path, out, va, te, fp32_sess, labels, n_calib=200, n_check=400):
    """Static INT8 (QDQ). Kept only if test accuracy drops <= 1 point (Technical Doc section 5)."""
    import onnxruntime as ort
    from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process

    class Reader(CalibrationDataReader):
        def __init__(self):
            idx = np.random.default_rng(0).permutation(len(va))[:n_calib]
            self.it = iter([{"input": va[i][0].unsqueeze(0).numpy()} for i in idx])

        def get_next(self):
            return next(self.it, None)

    pre = out / "model.pre.onnx"
    q = out / "model.int8.onnx"
    quant_pre_process(str(fp32_path), str(pre))
    quantize_static(str(pre), str(q), Reader(), quant_format=QuantFormat.QDQ,
                    activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8, per_channel=True)
    qs = ort.InferenceSession(str(q), providers=["CPUExecutionProvider"])
    idx = np.random.default_rng(1).permutation(len(te))[:n_check]
    a32 = aq = 0
    for i in idx:
        x, y = te[i]
        x = x.unsqueeze(0).numpy()
        a32 += int(fp32_sess.run(["logits"], {"input": x})[0].argmax() == y)
        aq += int(qs.run(["logits"], {"input": x})[0].argmax() == y)
    drop = (a32 - aq) / len(idx) * 100
    print(f"INT8: {q.stat().st_size / 1e6:.1f} MB, accuracy drop {drop:.1f} points on {len(idx)} test images")
    pre.unlink(missing_ok=True)
    if drop <= 1.0:
        return "model.int8.onnx"
    print("INT8 rejected (drop > 1 point); shipping FP32.")
    return None


if __name__ == "__main__":
    main()
