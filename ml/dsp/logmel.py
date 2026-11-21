"""Reference log-Mel front end (numpy/scipy only). THE source of truth.

Spec (Technical Documentation v1.1, section 6.1):
  16 kHz mono, 5.0 s = 80,000 samples
  STFT n_fft 1024, hop 256, periodic Hann, no centering -> 309 frames
  64 mel bins, 50-8000 Hz, Slaney mel scale + Slaney area norm (librosa default), power spectrum
  10*log10(mel + 1e-10), clip to (max - 80 dB), per-clip mean/std normalisation
  model input float32 [1, 1, 64, 309]

The browser must reproduce this exactly. `export_constants()` writes the window and
filterbank to JSON so the TypeScript side loads the same numbers instead of re-deriving them.
"""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache
from math import gcd
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

SR = 16_000
N_SAMPLES = 80_000
N_FFT = 1024
HOP = 256
N_MELS = 64
FMIN, FMAX = 50.0, 8000.0
TOP_DB = 80.0
EPS = 1e-10
N_FRAMES = (N_SAMPLES - N_FFT) // HOP + 1  # 309


# ---------------------------------------------------------------- audio I/O
def load_audio(path: str | Path) -> np.ndarray:
    """Any format ffmpeg reads -> float32 mono at 16 kHz in [-1, 1]."""
    path = str(path)
    if path.lower().endswith(".wav"):
        try:
            from scipy.io import wavfile
            sr, x = wavfile.read(path)
            return resample_to_16k(_to_float_mono(x), sr)
        except Exception:
            pass  # unusual WAV (e.g. 24-bit float variants): use ffmpeg
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def _to_float_mono(x: np.ndarray) -> np.ndarray:
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768.0
    elif x.dtype == np.int32:
        x = x.astype(np.float32) / 2147483648.0
    elif x.dtype == np.uint8:
        x = (x.astype(np.float32) - 128) / 128.0
    x = x.astype(np.float32)
    return x.mean(axis=1) if x.ndim == 2 else x


def resample_to_16k(x: np.ndarray, sr: int) -> np.ndarray:
    if sr == SR:
        return x.astype(np.float32)
    g = gcd(SR, sr)
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


def fix_length(x: np.ndarray, n: int = N_SAMPLES) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))


def windows(x: np.ndarray, hop_s: float = 2.5) -> list[np.ndarray]:
    """Slice a long recording into 5 s windows (training data). Short clips are padded."""
    if len(x) <= N_SAMPLES:
        return [fix_length(x)]
    step = int(hop_s * SR)
    return [x[s:s + N_SAMPLES] for s in range(0, len(x) - N_SAMPLES + 1, step)]


# ------------------------------------------------------------- filterbank
def _hz_to_mel(f):
    f = np.asanyarray(f, dtype=np.float64)
    f_sp, min_log_hz = 200.0 / 3, 1000.0
    min_log_mel, logstep = min_log_hz / f_sp, np.log(6.4) / 27.0
    return np.where(f >= min_log_hz, min_log_mel + np.log(np.maximum(f, 1e-12) / min_log_hz) / logstep, f / f_sp)


def _mel_to_hz(m):
    m = np.asanyarray(m, dtype=np.float64)
    f_sp, min_log_hz = 200.0 / 3, 1000.0
    min_log_mel, logstep = min_log_hz / f_sp, np.log(6.4) / 27.0
    return np.where(m >= min_log_mel, min_log_hz * np.exp(logstep * (m - min_log_mel)), f_sp * m)


@lru_cache(maxsize=1)
def mel_filterbank() -> np.ndarray:
    """[N_MELS, N_FFT//2+1], equivalent to librosa.filters.mel(sr=16000, n_fft=1024,
    n_mels=64, fmin=50, fmax=8000) with htk=False, norm='slaney'."""
    fft_f = np.fft.rfftfreq(N_FFT, 1.0 / SR)
    mel_f = _mel_to_hz(np.linspace(_hz_to_mel(FMIN), _hz_to_mel(FMAX), N_MELS + 2))
    fdiff = np.diff(mel_f)
    ramps = mel_f[:, None] - fft_f[None, :]
    lower = -ramps[:-2] / fdiff[:-1, None]
    upper = ramps[2:] / fdiff[1:, None]
    w = np.maximum(0, np.minimum(lower, upper))
    w *= (2.0 / (mel_f[2:] - mel_f[:-2]))[:, None]
    return w.astype(np.float32)


@lru_cache(maxsize=1)
def hann() -> np.ndarray:
    n = np.arange(N_FFT)
    return (0.5 - 0.5 * np.cos(2 * np.pi * n / N_FFT)).astype(np.float32)  # periodic


# ---------------------------------------------------------------- features
def power_spectrogram(x: np.ndarray) -> np.ndarray:
    x = fix_length(x.astype(np.float32))
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(N_FRAMES)[:, None]
    frames = x[idx] * hann()[None, :]
    return (np.abs(np.fft.rfft(frames.astype(np.float64), axis=1)) ** 2).T  # [513, 309]


def logmel_db(x: np.ndarray) -> np.ndarray:
    """dB log-Mel before normalisation, [64, 309]. Used for quality checks and parity."""
    mel = mel_filterbank().astype(np.float64) @ power_spectrogram(x)
    db = 10.0 * np.log10(mel + EPS)
    return np.maximum(db, db.max() - TOP_DB)


def logmel(x: np.ndarray) -> np.ndarray:
    """Normalised model features, float32 [64, 309]."""
    db = logmel_db(x)
    return ((db - db.mean()) / (db.std() + 1e-6)).astype(np.float32)


def model_input(x: np.ndarray) -> np.ndarray:
    return logmel(x)[None, None]  # [1, 1, 64, 309]


# ----------------------------------------------------------- quality gates
def quality(x: np.ndarray, floor_rms: float = 0.003, clip_frac: float = 0.01,
            low_frac: float = 0.6, flat_max: float = 0.5,
            wind_cv: float = 0.8) -> tuple[bool, str]:
    """Starting thresholds from the spec; tune on field recordings."""
    x = fix_length(x)
    if np.sqrt(np.mean(x ** 2)) < floor_rms:
        return False, "too_quiet"
    if np.mean(np.abs(x) >= 0.999) > clip_frac:
        return False, "clipping"
    S = power_spectrogram(x)
    p = S.mean(axis=1)
    f = np.fft.rfftfreq(N_FFT, 1.0 / SR)
    # Wind = low-frequency dominated AND gusty. Engines/generators are also low-frequency
    # (a 3000 rpm generator hums at 50 Hz) but their energy is steady over time, so the
    # spec's "energy below 100 Hz" rule alone would reject real machines.
    low = S[f < 100].sum(axis=0)
    gusty = low.std() / (low.mean() + EPS) > wind_cv
    if p[f < 100].sum() / (p.sum() + EPS) > low_frac and gusty:
        return False, "wind"
    flat = np.exp(np.mean(np.log(p + EPS))) / (np.mean(p) + EPS)
    if flat > flat_max:
        return False, "no_machine"
    return True, "ok"


def export_constants(path: str | Path) -> None:
    """Window + filterbank + parameters for the TypeScript implementation."""
    fb = mel_filterbank()
    nz = [(int(np.nonzero(r)[0][0]), int(np.nonzero(r)[0][-1])) if r.any() else (0, -1) for r in fb]
    data = {
        "sample_rate": SR, "n_samples": N_SAMPLES, "n_fft": N_FFT, "hop": HOP, "n_frames": N_FRAMES,
        "n_mels": N_MELS, "fmin": FMIN, "fmax": FMAX, "top_db": TOP_DB, "eps": EPS,
        "log": "db = 10*log10(mel_power + eps); db = max(db, max(db) - top_db); "
               "out = (db - mean(db)) / (std(db) + 1e-6)  # std = population std",
        "window": "periodic hann: 0.5 - 0.5*cos(2*pi*n/n_fft)",
        "stft": "no centering, no padding; frame t starts at t*hop; power = |rfft|^2",
        # sparse rows: weights for bins [start..end] inclusive
        "mel_rows": [{"start": s, "weights": [float(v) for v in fb[i, s:e + 1]]} for i, (s, e) in enumerate(nz)],
    }
    Path(path).write_text(json.dumps(data))
