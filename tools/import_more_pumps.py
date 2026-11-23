"""Add more real pump machines to ml/data/raw, next to the 4 DCASE 2020 development pumps.

Sources (both Hitachi MIMII recordings, CC BY-NC-SA 4.0, research / non-commercial use):
  1. DCASE 2020 Task 2 evaluation set, pump IDs 01, 03, 05 (zenodo.org/record/3841772,
     eval_data_test_pump.zip) + its ground-truth list (zenodo.org/record/3951620, eval_data_list.csv).
  2. DCASE 2021 Task 2 development set = MIMII DUE, pump sections 00, 01, 02 (zenodo.org/record/4562016,
     dev_data_pump.zip). Each section is a different pump product; labels are in the file names.

    python tools/import_more_pumps.py --eval2020 /content/eval2020 --gt eval_data_list.csv \
                                      --dev2021 /content/dev2021 --dst ml/data/raw --per-class 150

Writes ml/data/raw/{healthy,faulty}/<machine>/... with one folder per physical machine, so
leave-one-machine-out keeps holding out a whole machine at once.
"""
from __future__ import annotations

import argparse
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path


def gt_pump_labels(csv_path: Path) -> dict[str, str]:
    """eval_data_list.csv: a machine-type line, then 'file,original,label' rows. Returns pump file -> label."""
    labels, section = {}, None
    for line in csv_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if "," not in line:
            section = line
            continue
        if section == "pump":
            f, _orig, lab = line.split(",")[:3]
            labels[f] = "faulty" if lab.strip() == "1" else "healthy"
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval2020", help="folder where eval_data_test_pump.zip was unzipped")
    ap.add_argument("--gt", help="eval_data_list.csv (ground truth for the 2020 evaluation set)")
    ap.add_argument("--dev2021", help="folder where dev_data_pump.zip (2021) was unzipped")
    ap.add_argument("--dst", default="ml/data/raw")
    ap.add_argument("--per-class", type=int, default=150, help="max clips per machine per label")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    groups: dict[tuple[str, str], list[Path]] = defaultdict(list)

    if a.eval2020:
        if not a.gt:
            raise SystemExit("--gt eval_data_list.csv is needed with --eval2020")
        labels = gt_pump_labels(Path(a.gt))
        pat = re.compile(r"^id_(\d+)_\d+\.wav$")
        missing = 0
        for f in Path(a.eval2020).rglob("*.wav"):
            if "pump" not in f.parts:
                continue
            m = pat.match(f.name)
            if not m:
                continue
            lab = labels.get(f.name)
            if lab is None:
                missing += 1
                continue
            groups[(lab, f"pump_id_{m.group(1)}")].append(f)
        print(f"2020 evaluation pumps: {sum(len(v) for k, v in groups.items())} labelled clips"
              + (f", {missing} without a label (skipped)" if missing else ""))

    if a.dev2021:
        pat = re.compile(r"^section_(\d+)_(source|target)_test_(normal|anomaly)_\d+\.wav$")
        n0 = sum(len(v) for v in groups.values())
        for f in Path(a.dev2021).rglob("*.wav"):
            if "pump" not in f.parts:
                continue
            m = pat.match(f.name)
            if m:
                lab = "healthy" if m.group(3) == "normal" else "faulty"
                groups[(lab, f"pump21_sec_{m.group(1)}")].append(f)
        print(f"2021 pump sections: {sum(len(v) for v in groups.values()) - n0} labelled test clips")

    if not groups:
        raise SystemExit("No pump clips found. Check the folders you passed.")

    rnd = random.Random(a.seed)
    dst = Path(a.dst)
    for (lab, machine), files in sorted(groups.items()):
        files = sorted(files)
        rnd.shuffle(files)
        out = dst / lab / machine
        out.mkdir(parents=True, exist_ok=True)
        for f in files[: a.per_class]:
            shutil.copy2(f, out / f.name)
        print(f"  {lab:8s} {machine:16s} {min(len(files), a.per_class):4d} clips")
    machines = sorted({m for _, m in groups})
    print(f"Added {len(machines)} machines: {machines}")


if __name__ == "__main__":
    main()
