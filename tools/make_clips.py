"""Pre-generate every voice clip for a language (run once; ship the clips; app stays offline).
  yarngpt: Hausa, Yoruba, Igbo, Nigerian English (pip install yarngpt torch torchaudio; use Colab GPU)
  abena  : Swahili, Twi (HTTP API; optional ABENA_API_KEY; buy a little credit first)
    python tools/make_clips.py ha --dry-run
    python tools/make_clips.py sw --provider abena --voice amani_swh
"""
from __future__ import annotations
import argparse, base64, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gateway"))
from app.engine import Content  # noqa: E402
from app.voice import clip_catalogue  # noqa: E402

YARN_LANG = {"ha": "hausa", "yo": "yoruba", "ig": "igbo", "en": "english"}
YARN_VOICES = {"hausa": ["amina", "fatima", "ibrahim", "yusuf"], "yoruba": ["abayomi", "aisha", "folake"],
               "igbo": ["chioma", "obinna", "adanna"],
               "english": ["idera", "chinenye", "jude", "emma", "umar", "joke", "zainab", "osagie", "remi", "tayo"]}
ABENA_URL = "https://abena.mobobi.com/playground/api/v1/tts/synthesize/"
ABENA_DEFAULT = {"sw": "amani_swh", "tw": "abena_twi_medium"}


def to_mp3(wav: Path, mp3: Path) -> None:
    base = ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", "22050"]
    try:
        subprocess.run(base + ["-af", "loudnorm=I=-18:TP=-2", "-b:a", "32k", str(mp3)], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        subprocess.run(base + ["-b:a", "32k", str(mp3)], check=True)


class YarnGPT:
    def __init__(self, lang, voice):
        if lang not in YARN_LANG:
            sys.exit(f"yarngpt supports {sorted(YARN_LANG)}; use abena for {lang}")
        self.language = YARN_LANG[lang]
        self.voice = voice or YARN_VOICES[self.language][0]
        from yarngpt import generate_speech
        import torchaudio
        self.gen, self.ta = generate_speech, torchaudio

    def wav(self, text, out):
        audio = self.gen(text, speaker=self.voice, language=self.language)
        if hasattr(audio, "dim") and audio.dim() == 1:
            audio = audio.unsqueeze(0)
        self.ta.save(str(out), audio.detach().cpu() if hasattr(audio, "detach") else audio, sample_rate=24000)


class Abena:
    def __init__(self, lang, voice):
        self.voice = voice or ABENA_DEFAULT.get(lang)
        if not self.voice:
            sys.exit(f"no default Abena voice for {lang}; pass --voice")
        self.key = os.environ.get("ABENA_API_KEY")

    def wav(self, text, out):
        body = json.dumps({"text": text, "voice": self.voice, "speed": 1.0}).encode()
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
            headers["Idempotency-Key"] = f"aa-{self.voice}-{abs(hash(text)) % 10**12}"
        for _ in range(6):
            req = urllib.request.Request(ABENA_URL, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    out.write_bytes(base64.b64decode(json.loads(r.read().decode())["audio_base64"]))
                return
            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    time.sleep(int(e.headers.get("Retry-After", "10")))
                    continue
                if e.code == 402:
                    sys.exit("Abena: out of credits (402). Add credit, then rerun with --only-missing.")
                raise
        raise RuntimeError("Abena: too many retries")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lang")
    ap.add_argument("--provider", choices=["yarngpt", "abena"])
    ap.add_argument("--voice")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--allow-unreviewed", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    content = Content(ROOT / "content", allow_unreviewed=True)
    if a.lang not in content.phrases:
        sys.exit(f"No phrase pack content/phrases/{a.lang}.json")
    cat = clip_catalogue(content, a.lang)
    if a.limit:
        cat = dict(list(cat.items())[: a.limit])
    chars = sum(len(t) for t in cat.values())
    print(f"{a.lang}: {len(cat)} clips, {chars} characters")
    if a.dry_run:
        for k, v in cat.items():
            print(f"  {k:32s} {v}")
        return
    if not content.phrases[a.lang].get("reviewed") and not a.allow_unreviewed:
        sys.exit(f"{a.lang} is not reviewed by a native speaker. Use --allow-unreviewed only to test.")
    if not a.provider:
        sys.exit("--provider yarngpt|abena required")
    tts = YarnGPT(a.lang, a.voice) if a.provider == "yarngpt" else Abena(a.lang, a.voice)
    out_dir = ROOT / "content" / "clips" / a.lang
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (cid, text) in enumerate(cat.items(), 1):
            mp3 = out_dir / f"{cid}.mp3"
            if a.only_missing and mp3.exists():
                continue
            wav = Path(tmp) / f"{cid}.wav"
            tts.wav(text, wav)
            to_mp3(wav, mp3)
            print(f"[{i}/{len(cat)}] {cid}")
    print(f"Done: clips in {out_dir}. Have a native speaker listen to a sample.")


if __name__ == "__main__":
    main()