"""HTTP-level tests replaying Africa's Talking-style callbacks. Needs fastapi + httpx."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as m  # noqa: E402

client = TestClient(m.app)
sent = []


@pytest.fixture(autouse=True)
def fake_sms(monkeypatch):
    sent.clear()
    monkeypatch.setattr(m, "send_sms", lambda to, msg: sent.append((to, msg)))
    monkeypatch.setattr(m, "TOKEN", "")   # tests ignore the CALLBACK_TOKEN from .env


def test_token_enforced(monkeypatch):
    monkeypatch.setattr(m, "TOKEN", "s3cret")
    assert ussd("").status_code == 403
    r = client.post("/ussd?token=s3cret", data={"sessionId": "t", "serviceCode": "*384#",
                                               "phoneNumber": "+2348012345678", "text": ""})
    assert r.status_code == 200 and r.text.startswith("CON ")
    r = client.post("/ussd/s3cret", data={"sessionId": "t", "serviceCode": "*384#",
                                         "phoneNumber": "+2348012345678", "text": ""})
    assert r.status_code == 200 and r.text.startswith("CON ")
    assert client.post("/ussd/wrong", data={"sessionId": "t", "phoneNumber": "+2348012345678"}).status_code == 403


def ussd(text, sid="ATUid_1"):
    return client.post("/ussd", data={"sessionId": sid, "serviceCode": "*384*1#",
                                      "phoneNumber": "+2348012345678", "text": text})


def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"]


def test_ussd_full_session_sends_sms():
    assert ussd("").text.startswith("CON ")
    assert ussd("1").text.startswith("CON ")
    r = ussd("1*1*1")
    assert r.text.startswith("END Possible cassava mosaic")
    assert sent and sent[0][0] == "+2348012345678"


def test_voice_call():
    form = {"sessionId": "ATVId_1", "isActive": "1", "callerNumber": "+2348012345678"}
    r = client.post("/voice", data=form)
    assert "<GetDigits" in r.text and "Welcome" in r.text
    for _ in range(2):
        client.post("/voice", data={**form, "dtmfDigits": "1"})
    r = client.post("/voice", data={**form, "dtmfDigits": "1"})
    assert "cassava mosaic" in r.text
    r = client.post("/voice", data={**form, "dtmfDigits": "2"})
    assert "SMS" in r.text and sent
    assert client.post("/voice", data={**form, "isActive": "0"}).status_code == 200


def test_no_raw_numbers_stored():
    ussd("1*1*1", sid="x")
    rows = m.events.db.execute("SELECT phone_hash FROM events").fetchall()
    assert rows and all("2348012345678" not in r[0] for r in rows)


def test_agent_send(monkeypatch):
    monkeypatch.setattr(m, "AGENT_KEYS", ["k1"])
    body = {"farmer_phone": "08031234567", "lang": "en", "diagnosis_id": "machine_fault"}
    assert client.post("/agent/send", json=body).status_code == 401
    r = client.post("/agent/send", json=body, headers={"X-Agent-Key": "k1"})
    assert r.status_code == 200 and r.json()["queued"] and sent[-1][0] == "+2348031234567"
