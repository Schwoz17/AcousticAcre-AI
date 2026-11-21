"""Build a .aapack (zip + manifest with SHA-256 per file), per Technical Documentation section 9.

    python tools/pack_builder.py machine --run ml/runs/baseline --out packs/
    python tools/pack_builder.py crop    --run ml/runs/crop     --out packs/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_machine(run: Path, pack_id: str, version: str, out: Path) -> Path:
    params = json.loads((run / "pack_params.json").read_text())
    model = run / "model.onnx"
    labels_path = run / "labels.json"
    # label -> diagnosis ID mapping used by app and phrase library
    diag = {"healthy": "machine_healthy", "faulty": "machine_fault"}
    labels_path.write_text(json.dumps(
        [{"index": i, "label": l, "diagnosis_id": diag.get(l, f"machine_{l}")}
         for i, l in enumerate(params["labels"])], indent=2))
    manifest = {
        "pack_id": pack_id, "type": "machine", "version": version, "min_app_version": "1.0.0",
        "model": "model.onnx", "labels": "labels.json",
        "input": {"kind": "audio_logmel", "name": "input", "shape": [1, 1, 64, 309],
                  "sample_rate": 16000, "seconds": 5.0, "dsp": "dsp_constants.json"},
        "output": {"name": "logits"},
        "temperature": params["temperature"],
        "thresholds": params["thresholds"],
        "files": {},
    }
    files = [model, labels_path]
    dsp = run / "dsp_constants.json"
    if dsp.exists():
        files.append(dsp)
    for f in files:
        manifest["files"][f.name] = sha256(f)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{pack_id}-{version}.aapack"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        for f in files:
            z.write(f, f.name)
    return dest


def build_crop(run: Path, pack_id: str, version: str, out: Path) -> Path:
    params = json.loads((run / "pack_params.json").read_text())
    model = run / params.get("model_file", "model.onnx")
    labels_path = run / "labels.json"
    manifest = {
        "pack_id": pack_id, "type": "crop", "version": version, "min_app_version": "1.0.0",
        "crops": sorted({l.split("_")[0] for l in params["labels"]}),
        "model": model.name, "labels": "labels.json",
        "input": {"kind": "image", "name": "input", "shape": [1, 3, 224, 224], **params["input"]},
        "output": {"name": "logits", "cam": "cam"},
        "temperature": params["temperature"],
        "thresholds": params["thresholds"],
        "files": {},
    }
    files = [model, labels_path]
    for f in files:
        manifest["files"][f.name] = sha256(f)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{pack_id}-{version}.aapack"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        for f in files:
            z.write(f, f.name)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["machine", "crop"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--id", default=None)
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--out", default="packs")
    a = ap.parse_args()
    fn = build_machine if a.kind == "machine" else build_crop
    print("Wrote", fn(Path(a.run), a.id or f"{a.kind}-core-1", a.version, Path(a.out)))


if __name__ == "__main__":
    main()
