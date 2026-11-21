"""Export the baseline (log-Mel stats -> logistic regression) as ONNX.

Same contract as the CNN, so the frontend does not care which model it gets:
    input  "input"  float32 [N, 1, 64, 309]   (normalised log-Mel from dsp/logmel.py)
    output "logits" float32 [N, C]            (apply softmax(logits / T) with T from the manifest)

    pip install onnx onnxruntime numpy
    python -m export.baseline_to_onnx --run runs/baseline
Writes runs/baseline/model.onnx and checks it against numpy before you ship it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dsp.logmel import N_FRAMES, N_MELS  # noqa: E402


def numpy_forward(x: np.ndarray, m) -> np.ndarray:
    """Reference forward pass, identical to train.audio_baseline.features + sklearn."""
    lm = x[:, 0]                                    # [N,64,309]
    f = np.concatenate([lm.mean(axis=2), lm.std(axis=2)], axis=1)
    z = (f - m["mean"]) / m["scale"]
    return z @ m["W"].T + m["b"]


def build(m, opset=17):
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    C = m["W"].shape[0]
    init = [
        numpy_helper.from_array(m["mean"].astype(np.float32), "mu"),
        numpy_helper.from_array(m["scale"].astype(np.float32), "sigma"),
        numpy_helper.from_array(m["W"].T.astype(np.float32), "Wt"),
        numpy_helper.from_array(m["b"].astype(np.float32), "b"),
        numpy_helper.from_array(np.array([-1, 2 * N_MELS], dtype=np.int64), "flat_shape"),
    ]
    nodes = [
        helper.make_node("ReduceMean", ["input"], ["mean_k"], axes=[3], keepdims=1),
        helper.make_node("Sub", ["input", "mean_k"], ["diff"]),
        helper.make_node("Mul", ["diff", "diff"], ["sq"]),
        helper.make_node("ReduceMean", ["sq"], ["var_k"], axes=[3], keepdims=1),
        helper.make_node("Sqrt", ["var_k"], ["std_k"]),
        helper.make_node("Concat", ["mean_k", "std_k"], ["feat4"], axis=2),   # [N,1,128,1]
        helper.make_node("Reshape", ["feat4", "flat_shape"], ["feat"]),       # [N,128]
        helper.make_node("Sub", ["feat", "mu"], ["c"]),
        helper.make_node("Div", ["c", "sigma"], ["z"]),
        helper.make_node("MatMul", ["z", "Wt"], ["zw"]),
        helper.make_node("Add", ["zw", "b"], ["logits"]),
    ]
    g = helper.make_graph(
        nodes, "acousticacre_machine_baseline",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, ["N", 1, N_MELS, N_FRAMES])],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["N", C])],
        init)
    model = helper.make_model(g, opset_imports=[helper.make_opsetid("", opset)],
                              producer_name="acousticacre")
    model.ir_version = 8  # broadly supported by onnxruntime-web
    onnx.checker.check_model(model)
    return model


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/baseline")
    a = ap.parse_args(argv)
    run = Path(a.run)
    m = dict(np.load(run / "model.npz"))
    model = build(m)
    out = run / "model.onnx"
    out.write_bytes(model.SerializeToString())

    import onnxruntime as ort
    sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
    x = np.random.default_rng(0).normal(size=(4, 1, N_MELS, N_FRAMES)).astype(np.float32)
    got = sess.run(["logits"], {"input": x})[0]
    want = numpy_forward(x, m)
    err = float(np.abs(got - want).max())
    print(f"Wrote {out} ({out.stat().st_size / 1024:.1f} KB); ONNX vs numpy max abs diff {err:.2e}")
    if err > 1e-3:
        sys.exit("MISMATCH: do not ship this model")


if __name__ == "__main__":
    main()
