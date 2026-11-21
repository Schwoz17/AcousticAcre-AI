"""Turn the DCASE 2020 Task 2 pump data (real MIMII pumps) into our training layout.

Files are named  <normal|anomaly>_id_<NN>_<n>.wav  inside dev_data/pump/{train,test}/.
The test folder holds both normal and anomaly clips for every pump ID; train holds normal only.

    python tools/import_dcase.py /path/to/pump  ml/data/raw  [--per-class 150] [--copy]

Result:
    ml/data/raw/healthy/pump_id_00/...   ml/data/raw/faulty/pump_id_00/...
The machine folder name is the same under both labels, so leave-one-machine-out
holds out a whole pump (its normal AND its faulty clips) at once.
"""
import argparse
import os
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

PAT = re.compile(r"(normal|anomaly)_id_(\d+)_\d+\.wav$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="folder containing train/ and/or test/ (e.g. dev_data/pump)")
    ap.add_argument("dst", help="e.g. ml/data/raw")
    ap.add_argument("--per-class", type=int, default=150, help="max clips per pump per label (balance)")
    ap.add_argument("--copy", action="store_true", help="copy instead of symlink")
    ap.add_argument("--prefix", default="pump")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    groups = defaultdict(list)  # (label, machine) -> files
    for f in Path(a.src).rglob("*.wav"):
        m = PAT.search(f.name)
        if m:
            label = "healthy" if m.group(1) == "normal" else "faulty"
            groups[(label, f"{a.prefix}_id_{m.group(2)}")].append(f)
    if not groups:
        raise SystemExit(f"No files like normal_id_00_00000000.wav under {a.src}")

    rnd = random.Random(a.seed)
    for (label, machine), files in sorted(groups.items()):
        files = sorted(files)
        rnd.shuffle(files)
        files = files[: a.per_class]
        d = Path(a.dst) / label / machine
        d.mkdir(parents=True, exist_ok=True)
        for f in files:
            t = d / f"{f.parent.name}_{f.name}"   # train/ and test/ reuse names
            if t.exists():
                continue
            if a.copy:
                shutil.copy2(f, t)
            else:
                os.symlink(f.resolve(), t)
        print(f"{label:>8} / {machine}: {len(files)} clips")


if __name__ == "__main__":
    main()
