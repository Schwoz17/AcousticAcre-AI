"""Write DSP parity fixtures: 16 kHz clips + Python reference outputs for the TS test.

    python tools/parity_fixtures.py [audio files...]   (no args = synthetic clips)
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from dsp.logmel import load_audio, windows, logmel_db, logmel, quality, export_constants, fix_length

out = Path(__file__).resolve().parents[1] / "web-dsp" / "fixtures"
out.mkdir(parents=True, exist_ok=True)
export_constants(out / "dsp_constants.json")
clips = []
if len(sys.argv) > 1:
    for f in sys.argv[1:]:
        clips += windows(load_audio(f))[:3]
else:
    rng = np.random.default_rng(42); t = np.arange(80000) / 16000
    for i in range(20):
        f0 = rng.uniform(30, 400)
        x = sum(rng.uniform(.02, .3) * np.sin(2*np.pi*f0*k*t + rng.uniform(0, 6)) for k in range(1, 6))
        x = x + rng.uniform(.001, .05) * rng.normal(size=t.size)
        if i % 5 == 0: x = x * (rng.uniform(size=t.size) > .3)          # rough texture
        if i == 19: x = np.zeros_like(t)                                  # silence edge case
        clips.append(fix_length(x.astype(np.float32)))
clips = clips[:20]
np.stack(clips).astype("<f4").tofile(out / "clips_f32le.bin")
ref = {"n": len(clips),
       "db": [logmel_db(c).astype(np.float64).ravel().tolist()[::7] for c in clips],    # every 7th value
       "norm": [logmel(c).ravel().tolist()[::7] for c in clips],
       "quality": [quality(c)[1] for c in clips]}
(out / "reference.json").write_text(json.dumps(ref))
print(f"wrote {len(clips)} clips to {out}")
