"""SMOKE TEST ONLY: writes fake machine sounds so you can check the ML pipeline runs.
Never report numbers from this data.   python tools/smoke_synth.py /tmp/synth"""
import sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
rng = np.random.default_rng(0); root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/synth"); sr = 44100
def machine(f0, faulty, secs=30):
    t = np.arange(int(secs * sr)) / sr
    x = sum(a * np.sin(2 * np.pi * f0 * k * t + rng.uniform(0, 6)) for k, a in [(1, .3), (2, .15), (3, .07), (5, .03)])
    if faulty:
        x = x + (np.sin(2 * np.pi * f0 / 2 * t) > 0.98) * rng.normal(0, .3, len(t)) + 0.04 * np.sin(2 * np.pi * 2800 * t)
    x = x + rng.normal(0, .02, len(t))
    return (np.clip(x * rng.uniform(.5, 1.2), -1, 1) * 32767).astype(np.int16)
for label, faulty in [("healthy", 0), ("faulty", 1)]:
    for m in range(4):
        d = root / label / f"{label}_m{m}"; d.mkdir(parents=True, exist_ok=True)
        f0 = rng.uniform(40, 120)
        for r in range(2):
            wavfile.write(d / f"rec{r}.wav", sr, machine(f0, faulty))
print("wrote", root)
