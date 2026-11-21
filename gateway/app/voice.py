"""Voice (IVR) responses in Africa's Talking voice XML.

Everything spoken is a list of (clip_id, text) segments. For each segment we <Play>
content/clips/<lang>/<clip_id>.mp3 if it exists, otherwise fall back to provider TTS
(<Say>). `clip_catalogue()` lists every segment a language can ever need, so
tools/make_clips.py generates exactly the clips this module plays.
"""
from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from .engine import UNCERTAIN, Content, Flow, Screen

POST_RESULT_REPEAT, POST_RESULT_SMS, POST_RESULT_HUMAN = "1", "2", "9"
SKIP_UI = {"press_option", "help_line", "yes", "no", "choose_language"}


def _options(c: Content, lang: str, names: list[str]) -> str:
    tmpl = c.ui(lang, "press_option")
    return " ".join(tmpl.format(n=i, option=o) for i, o in enumerate(names, 1))


def question_text(c: Content, lang: str, qid: str) -> str:
    q = c.phrases[lang]["questions"][qid]
    return f"{q} {_options(c, lang, [c.ui(lang, 'yes'), c.ui(lang, 'no')])}"


def crop_menu_text(c: Content, lang: str) -> str:
    names = [c.phrases[lang]["crops"].get(k, k.title()) for k in c.crops]
    return f"{c.ui(lang, 'choose_crop')} {_options(c, lang, names)}"


def lang_option_text(c: Content, lang: str, n: int) -> str:
    return c.phrases[lang]["ui"]["press_option"].format(n=n, option=c.phrases[lang]["lang_name"])


def result_segments(c: Content, lang: str, diag: str) -> list[tuple[str, str]]:
    if diag == UNCERTAIN:
        segs = [("not_sure", c.ui(lang, "not_sure")),
                ("s_ask_extension_officer", c.phrases[lang]["steps"]["ask_extension_officer"]["text"])]
    else:
        segs = [(f"d_{diag}", c.diagnosis_name(lang, diag))]
        segs += [(f"s_{s}", c.phrases[lang]["steps"][s]["text"]) for s in c.diagnoses[diag]["steps"]]
    return segs + [("disclaimer", c.ui(lang, "disclaimer"))]


def screen_segments(c: Content, s: Screen, first: bool = False):
    lang, segs = s.lang, []
    if first:
        segs.append((lang, "welcome", c.ui(lang, "welcome")))
    if s.error:
        segs.append((lang, "invalid", c.ui(lang, "invalid")))
    if s.kind == "result":
        segs += [(lang, cid, t) for cid, t in result_segments(c, lang, s.result)]
        segs.append((lang, "repeat_or_help", c.ui(lang, "repeat_or_help")))
    elif s.prompt_id == "choose_language":
        for i, l in enumerate(c.langs, 1):
            segs.append((l, f"press_lang_{i}", lang_option_text(c, l, i)))
    elif s.prompt_id == "choose_crop":
        segs.append((lang, "crop_menu", crop_menu_text(c, lang)))
    else:
        segs.append((lang, s.prompt_id, question_text(c, lang, s.prompt_id)))
    return segs


def clip_catalogue(c: Content, lang: str) -> dict[str, str]:
    cat = {k: v for k, v in c.phrases[lang]["ui"].items()
           if k not in SKIP_UI and "[" not in v and "{" not in v}
    cat["crop_menu"] = crop_menu_text(c, lang)
    for qid in c.phrases[lang]["questions"]:
        cat[qid] = question_text(c, lang, qid)
    for d in c.diagnoses:
        cat[f"d_{d}"] = c.diagnosis_name(lang, d)
    for sid, v in c.phrases[lang]["steps"].items():
        cat[f"s_{sid}"] = v["text"]
    for n in range(1, 7):
        cat[f"press_lang_{n}"] = lang_option_text(c, lang, n)
    return cat


def _speak(c: Content, lang: str, clip_id, text: str, base_url: str) -> str:
    if clip_id and (c.root / "clips" / lang / f"{clip_id}.mp3").exists():
        return f"<Play url={quoteattr(f'{base_url}/clips/{lang}/{clip_id}.mp3')}/>"
    return f"<Say>{escape(text)}</Say>"


def _wrap(inner: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>'


def _gather(inner: str, base_url: str, token: str) -> str:
    cb = f"{base_url}/voice" + (f"/{token}" if token else "")
    return f'<GetDigits timeout="20" numDigits="1" callbackUrl={quoteattr(cb)}>{inner}</GetDigits>'


def screen_xml(content: Content, s: Screen, base_url: str, token: str = "", first: bool = False) -> str:
    inner = "".join(_speak(content, l, cid, t, base_url) for l, cid, t in screen_segments(content, s, first))
    no_input = _speak(content, s.lang, "no_input", content.ui(s.lang, "no_input"), base_url)
    return _wrap(_gather(inner, base_url, token) + no_input)


def dial_xml(content: Content, lang: str, officer_number, base_url: str = "") -> str:
    if not officer_number:
        return _wrap(_speak(content, lang, "no_officer", content.ui(lang, "no_officer"), base_url))
    return _wrap(_speak(content, lang, "connecting", content.ui(lang, "connecting"), base_url)
                 + f"<Dial phoneNumbers={quoteattr(officer_number)}/>")


def say_end(content: Content, lang: str, key: str, base_url: str = "") -> str:
    return _wrap(_speak(content, lang, key, content.ui(lang, key), base_url))


def flow_for(content: Content, tokens: list[str]) -> Flow:
    return Flow.replay(content, tokens)