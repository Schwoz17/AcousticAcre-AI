"""Channel-independent triage engine.

A Flow consumes keypad tokens ("1", "2", ...) one at a time and produces a
Screen. USSD and voice both drive the same Flow, so they always agree.
No web framework imports here, so it can be tested anywhere.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

UNCERTAIN = "UNCERTAIN"
YES, NO = "1", "2"


class Content:
    """Loads diagnoses, phrase packs and decision trees from the content dir."""

    def __init__(self, root: str | Path, allow_unreviewed: bool = False):
        root = Path(root)
        self.root = root
        self.diagnoses = {k: v for k, v in _load(root / "diagnoses.json").items() if not k.startswith("_")}
        self.phrases: dict[str, dict] = {}
        only = [l for l in os.environ.get("DEMO_LANGS", "").split(",") if l]
        for f in sorted((root / "phrases").glob("*.json")):
            p = _load(f)
            if only and p["lang"] not in only:
                continue
            if p.get("reviewed") or allow_unreviewed:
                self.phrases[p["lang"]] = p
        if "en" in self.phrases:  # English first in menus
            self.phrases = {"en": self.phrases["en"], **{k: v for k, v in self.phrases.items() if k != "en"}}
        self.trees = {f.stem: _load(f) for f in sorted((root / "trees").glob("*.json"))}
        self._validate()

    @property
    def langs(self) -> list[str]:
        return list(self.phrases)

    @property
    def crops(self) -> list[str]:
        return list(self.trees)

    def _validate(self) -> None:
        if not self.phrases:
            raise ValueError("No language packs loaded (none reviewed?)")
        for crop, tree in self.trees.items():
            nodes = tree["nodes"]
            if tree["start"] not in nodes:
                raise ValueError(f"{crop}: start node missing")
            for nid, n in nodes.items():
                for branch in ("yes", "no"):
                    t = n[branch]
                    if t not in nodes and t != UNCERTAIN and t not in self.diagnoses:
                        raise ValueError(f"{crop}.{nid}.{branch} -> unknown target {t}")
                for lang, p in self.phrases.items():
                    if n["prompt"] not in p["questions"]:
                        raise ValueError(f"{lang}: missing question {n['prompt']}")
        for lang, p in self.phrases.items():
            for d, spec in self.diagnoses.items():
                if d not in p["diagnoses"]:
                    raise ValueError(f"{lang}: missing diagnosis {d}")
                for s in spec["steps"]:
                    if s not in p["steps"]:
                        raise ValueError(f"{lang}: missing step {s}")

    # text helpers -------------------------------------------------------
    def ui(self, lang: str, key: str) -> str:
        return self.phrases[lang]["ui"][key]

    def diagnosis_name(self, lang: str, diag: str) -> str:
        if diag == UNCERTAIN:
            return self.ui(lang, "not_sure")
        return self.phrases[lang]["diagnoses"][diag]["name"]

    def steps(self, lang: str, diag: str) -> list[str]:
        if diag == UNCERTAIN:
            return [self.phrases[lang]["steps"]["ask_extension_officer"]["text"]]
        return [self.phrases[lang]["steps"][s]["text"] for s in self.diagnoses[diag]["steps"]]


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Screen:
    kind: str                     # "menu" | "question" | "result"
    lang: str
    title: str                    # text to show / speak
    options: list[str] = field(default_factory=list)  # numbered options, 1-based
    error: bool = False           # previous input was invalid
    result: str | None = None     # diagnosis id or UNCERTAIN
    crop: str | None = None
    prompt_id: str | None = None  # phrase id (for clip lookup)


class Flow:
    """language -> crop -> yes/no questions -> result."""

    def __init__(self, content: Content):
        self.c = content
        self.lang: str | None = content.langs[0] if len(content.langs) == 1 else None
        self.crop: str | None = content.crops[0] if len(content.crops) == 1 else None
        self.node: str | None = self.c.trees[self.crop]["start"] if self.crop else None
        self.result: str | None = None
        self.answers: list[str] = []
        self.error = False

    @classmethod
    def replay(cls, content: Content, tokens: list[str]) -> "Flow":
        f = cls(content)
        for t in tokens:
            f.feed(t)
        return f

    def feed(self, token: str) -> None:
        token = token.strip()
        self.error = False
        if self.result is not None:
            return  # finished; extra input ignored
        if self.lang is None:
            idx = _index(token, len(self.c.langs))
            if idx is None:
                self.error = True
            else:
                self.lang = self.c.langs[idx]
            return
        if self.crop is None:
            idx = _index(token, len(self.c.crops))
            if idx is None:
                self.error = True
            else:
                self.crop = self.c.crops[idx]
                self.node = self.c.trees[self.crop]["start"]
            return
        if token not in (YES, NO):
            self.error = True
            return
        self.answers.append(token)
        node = self.c.trees[self.crop]["nodes"][self.node]
        nxt = node["yes"] if token == YES else node["no"]
        if nxt in self.c.trees[self.crop]["nodes"]:
            self.node = nxt
        else:
            self.result = nxt
            self.node = None

    def screen(self) -> Screen:
        lang = self.lang or self.c.langs[0]
        if self.lang is None:
            return Screen("menu", lang, self.c.ui(lang, "choose_language"),
                          [self.c.phrases[l]["lang_name"] for l in self.c.langs], self.error,
                          prompt_id="choose_language")
        if self.crop is None:
            names = [self.c.phrases[lang]["crops"].get(k, k.title()) for k in self.c.crops]
            return Screen("menu", lang, self.c.ui(lang, "choose_crop"), names, self.error,
                          prompt_id="choose_crop")
        if self.result is None:
            pid = self.c.trees[self.crop]["nodes"][self.node]["prompt"]
            return Screen("question", lang, self.c.phrases[lang]["questions"][pid],
                          [self.c.ui(lang, "yes"), self.c.ui(lang, "no")], self.error,
                          crop=self.crop, prompt_id=pid)
        return Screen("result", lang, self.c.diagnosis_name(lang, self.result),
                      self.c.steps(lang, self.result), result=self.result, crop=self.crop)


def _index(token: str, n: int) -> int | None:
    if token.isdigit() and 1 <= int(token) <= n:
        return int(token) - 1
    return None


# ---------------------------------------------------------------- USSD ----
USSD_MAX_CHARS = 182  # common USSD screen limit [Verify per network]


def ussd_reply(content: Content, text: str) -> tuple[str, Flow]:
    """Africa's Talking sends the whole path, e.g. "1*1*2". Returns (reply, flow)."""
    tokens = [t for t in (text or "").split("*") if t != ""]
    flow = Flow.replay(content, tokens)
    s = flow.screen()
    if s.kind == "result":
        body = f"{s.title.rstrip('.')}.\n{s.options[0]}\n{content.ui(s.lang, 'sms_sent')}"
        if len(body) > USSD_MAX_CHARS - 4:   # long languages: drop the step, keep name + "sent by SMS"
            body = f"{s.title.rstrip('.')}.\n{content.ui(s.lang, 'sms_sent')}"
        return "END " + _fit(body), flow
    lines = []
    if s.error:
        lines.append(content.ui(s.lang, "invalid"))
    lines.append(s.title)
    lines += [f"{i}. {o}" for i, o in enumerate(s.options, 1)]
    if flow.lang is None and not s.error:
        # First screen: say plainly what is kept and for how long (NDPA), in every offered language.
        notes = []
        for l in content.langs:
            n = content.phrases[l]["ui"].get("privacy_sms")
            if n and n not in notes:
                notes.append(n)
        candidate = "\n".join(lines + notes)
        if len(candidate) <= USSD_MAX_CHARS - 4:
            lines += notes
    return "CON " + _fit("\n".join(lines)), flow


def _fit(s: str, limit: int = USSD_MAX_CHARS - 4) -> str:
    return s if len(s) <= limit else s[: limit - 1] + "…"


# ----------------------------------------------------------------- SMS ----
GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
           "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM7_EXT = set("^{}\\[~]|€")


def sms_segments(msg: str) -> tuple[str, int]:
    """Returns (encoding, segments) using standard GSM-7 / UCS-2 sizes."""
    if all(ch in GSM7 or ch in GSM7_EXT for ch in msg):
        n = sum(2 if ch in GSM7_EXT else 1 for ch in msg)
        return "GSM-7", 1 if n <= 160 else -(-n // 153)
    n = len(msg.encode("utf-16-le")) // 2
    return "UCS-2", 1 if n <= 70 else -(-n // 67)


def sms_text(content: Content, lang: str, diag: str, max_segments: int = 2, max_segments_ucs2: int = 3) -> str:
    """Diagnosis + as many steps as fit + help line + disclaimer. Always at least one step.
    UCS-2 languages (accented / hooked / tonal letters) get 3 segments since each holds only 67 chars."""
    head = f"AcousticAcre: {content.diagnosis_name(lang, diag).rstrip('.')}."
    tail = f" {content.ui(lang, 'help_line')} {content.ui(lang, 'disclaimer')}"
    steps = content.steps(lang, diag)
    msg = head + " 1) " + steps[0] + tail
    if sms_segments(msg)[0] == "UCS-2":
        max_segments = max_segments_ucs2
    for k in range(len(steps), 0, -1):
        cand = head + " " + " ".join(f"{i}) {s}" for i, s in enumerate(steps[:k], 1)) + tail
        if sms_segments(cand)[1] <= max_segments:
            msg = cand
            break
    # Privacy note (NDPA), only when it fits without making the SMS longer; it is always on the first USSD screen.
    privacy = content.phrases[lang]["ui"].get("privacy_sms")
    if privacy and sms_segments(msg + " " + privacy)[1] <= sms_segments(msg)[1]:
        msg = msg + " " + privacy
    return msg


def default_content_dir() -> Path:
    return Path(os.environ.get("CONTENT_DIR", Path(__file__).resolve().parents[2] / "content"))
