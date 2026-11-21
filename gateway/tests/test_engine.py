"""Engine tests: run with `pytest` from gateway/. No web framework needed."""
import itertools
import json
import shutil
from pathlib import Path

import pytest

from app.engine import (UNCERTAIN, Content, Flow, sms_segments, sms_text, ussd_reply,
                        USSD_MAX_CHARS)
from app.voice import screen_xml, dial_xml

CONTENT = Path(__file__).resolve().parents[2] / "content"


@pytest.fixture(scope="module")
def c():
    return Content(CONTENT)


@pytest.fixture
def c2(tmp_path):
    """Content with a second (fake, unreviewed) language to exercise the language menu."""
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    fr = json.loads((root / "phrases/en.json").read_text())
    fr.update(lang="xx", lang_name="Testlang", reviewed=False)
    (root / "phrases/xx.json").write_text(json.dumps(fr))
    return Content(root, allow_unreviewed=True)


def test_unreviewed_language_hidden(tmp_path, c2):
    assert Content(c2.root).langs == ["en"]
    assert c2.langs[0] == "en" and "xx" in c2.langs


def test_single_language_skips_menu_crop_menu_shown(c):
    reply, flow = ussd_reply(c, "")
    assert reply.startswith("CON Which crop?")
    assert "1. Cassava" in reply and "2. Maize" in reply and "3. Tomato" in reply
    reply, _ = ussd_reply(c, "1")
    assert "twisted" in reply and "1. Yes" in reply


@pytest.mark.parametrize("path,expected", [
    ("1*1*1", "cassava_mosaic"),
    ("1*1*2", None),            # still asking (mite question)
    ("1*1*2*1", "cassava_green_mite"),
    ("1*1*2*2", UNCERTAIN),
    ("1*2*1*1", "cassava_brown_streak"),
    ("1*2*1*2", UNCERTAIN),
    ("1*2*2*1", "cassava_bacterial_blight"),
    ("1*2*2*2*2", UNCERTAIN),
    ("2*1", "maize_fall_armyworm"), ("2*2*1", "maize_common_rust"), ("2*2*2*1", "maize_northern_leaf_blight"),
    ("2*2*2*2*1", "maize_streak_virus"), ("2*2*2*2*2", UNCERTAIN),
    ("3*1", "tomato_bacterial_wilt"), ("3*2*1", "tomato_yellow_leaf_curl"), ("3*2*2*1", "tomato_tuta_absoluta"),
    ("3*2*2*2*1", "tomato_late_blight"), ("3*2*2*2*2*1", "tomato_early_blight"), ("3*2*2*2*2*2", UNCERTAIN),
])
def test_tree_paths(c, path, expected):
    _, flow = ussd_reply(c, path)
    assert flow.result == expected


def test_every_path_terminates_and_fits_screen(c):
    seen = set()
    for crop in "123":
      for n in range(1, 7):
        for combo in itertools.product("12", repeat=n):
            reply, flow = ussd_reply(c, crop + "*" + "*".join(combo))
            assert reply.startswith(("CON ", "END "))
            assert len(reply) <= USSD_MAX_CHARS, reply
            if flow.result:
                seen.add(flow.result)
    in_trees = {n[b] for t in c.trees.values() for n in t["nodes"].values() for b in ("yes", "no")
                if n[b] not in t["nodes"]}
    assert in_trees == seen   # every leaf of every tree is reachable


def test_invalid_input_reprompts(c):
    reply, flow = ussd_reply(c, "7")
    assert reply.startswith("CON Invalid choice")
    assert flow.result is None
    reply, flow = ussd_reply(c, "7*1*1*1")   # invalid entry is skipped, path continues
    assert flow.result == "cassava_mosaic"


def test_result_screen(c):
    reply, _ = ussd_reply(c, "1*1*1")
    assert reply.startswith("END Possible cassava mosaic disease.")
    assert "SMS" in reply and ".." not in reply


def test_language_menu(c2):
    reply, _ = ussd_reply(c2, "")
    i = c2.langs.index("xx") + 1
    assert "1. English" in reply and f"{i}. Testlang" in reply
    _, flow = ussd_reply(c2, f"{i}*1*1*1")
    assert flow.lang == "xx" and flow.result == "cassava_mosaic"


def test_sms_fits_two_segments(c):
    for d in list(c.diagnoses) + [UNCERTAIN]:
        msg = sms_text(c, "en", d)
        enc, seg = sms_segments(msg)
        assert seg <= 2, (d, len(msg))
        assert "Guidance, not a guarantee." in msg and "1)" in msg


@pytest.fixture(scope="module")
def call():
    return Content(CONTENT, allow_unreviewed=True)


def test_all_languages_sms_and_ussd(call):
    """Every draft language: SMS always has a step and stays <= 3 segments; every USSD screen fits."""
    for li, lang in enumerate(call.langs, 1):
        for d in list(call.diagnoses) + [UNCERTAIN]:
            msg = sms_text(call, lang, d)
            assert "1)" in msg, (lang, d)
            assert sms_segments(msg)[1] <= 3, (lang, d, sms_segments(msg))
        for crop in "123":
            for combo in itertools.product("12", repeat=5):
                reply, _ = ussd_reply(call, f"{li}*{crop}*" + "*".join(combo))
                assert len(reply) <= USSD_MAX_CHARS, (lang, reply)
                assert not reply.endswith("…") or reply.startswith("CON"), (lang, reply)


def test_sms_encoding_detection():
    assert sms_segments("hello")[0] == "GSM-7"
    assert sms_segments("ɓarna ọ̀gbìn")[0] == "UCS-2"   # Hausa/Yoruba letters
    assert sms_segments("a" * 161) == ("GSM-7", 2)
    assert sms_segments("ɓ" * 71) == ("UCS-2", 2)


def test_voice_xml_question_and_result(c):
    x = screen_xml(c, Flow(c).screen(), "https://gw.example", first=True)
    assert x.startswith('<?xml') and "<GetDigits" in x and "Welcome" in x
    assert "Press 1 for Cassava." in x
    assert "Press 1 for Yes." in screen_xml(c, Flow.replay(c, ["1"]).screen(), "https://gw.example")
    f = Flow.replay(c, ["1", "1", "1"])
    x = screen_xml(c, f.screen(), "https://gw.example", token="t0k")
    assert "cassava mosaic" in x and "callbackUrl=\"https://gw.example/voice/t0k\"" in x
    assert "<Dial" in dial_xml(c, "en", "+2348000000000")
    assert "<Dial" not in dial_xml(c, "en", None)


def test_voice_xml_escapes(c):
    from xml.dom.minidom import parseString
    for path in (["1"], ["1", "1", "1"], ["1", "2", "2", "2", "2"], ["3", "1"]):
        parseString(screen_xml(c, Flow.replay(c, path).screen(), "https://a.b/?x=1&y=2"))


# ---------------------------------------------------------------- agent mode
from app import agent  # noqa: E402


def test_agent_key():
    with pytest.raises(agent.AgentError) as e:
        agent.check_key("x", [])
    assert e.value.status == 503
    with pytest.raises(agent.AgentError):
        agent.check_key("wrong", ["secret123"])
    assert agent.check_key("secret123", ["secret123"]) == "secret"


@pytest.mark.parametrize("raw,want", [("08031234567", "+2348031234567"), ("+254 712 345 678", "+254712345678"),
                                      ("002348031234567", "+2348031234567"), ("2348031234567", "+2348031234567")])
def test_agent_phone(raw, want):
    assert agent.normalise_phone(raw) == want


def test_agent_message(c):
    phone, lang, msg = agent.build_message(c, {"farmer_phone": "0803 123 4567", "lang": "zz",
                                               "diagnosis_id": "machine_fault"})
    assert phone == "+2348031234567" and lang == "en" and "fault" in msg
    with pytest.raises(agent.AgentError):
        agent.build_message(c, {"farmer_phone": "123", "diagnosis_id": "machine_fault"})
    with pytest.raises(agent.AgentError):
        agent.build_message(c, {"farmer_phone": "+2348031234567", "diagnosis_id": "nope"})
    assert "Not sure" in agent.build_message(c, {"farmer_phone": "+2348031234567", "diagnosis_id": "UNCERTAIN"})[2]
