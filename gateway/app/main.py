"""AcousticAcre gateway: Africa's Talking USSD, voice and SMS callbacks.

Run:  uvicorn app.main:app --reload --port 8000   (from the gateway/ folder)
"""
from __future__ import annotations

import logging
import os

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import agent, voice
from .engine import Content, Flow, default_content_dir, sms_text, ussd_reply
from .sms import send_sms
from .store import EventLog, RateLimiter, SessionStore, phone_hash

def _load_dotenv() -> None:
    """Read gateway/.env (KEY=VALUE lines) so Windows users don't need to export variables."""
    from pathlib import Path
    f = Path(__file__).resolve().parents[1] / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("gateway")

CONTENT_DIR = default_content_dir()
content = Content(CONTENT_DIR, allow_unreviewed=os.environ.get("ALLOW_UNREVIEWED") == "1")
SECRET = os.environ.get("HMAC_SECRET", "dev-only-change-me")
TOKEN = os.environ.get("CALLBACK_TOKEN", "")          # optional ?token= on callback URLs
OFFICER = os.environ.get("OFFICER_NUMBER")            # e.g. +2348000000000
USSD_CODE = os.environ.get("USSD_CODE", "[USSD code]")
AGENT_KEYS = [k for k in os.environ.get("AGENT_KEYS", "").split(",") if k]   # one key per agent
DEFAULT_CC = os.environ.get("DEFAULT_COUNTRY_CODE", "234")
ALLOWED_ORIGINS = [o for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o]  # the PWA origin

sessions = SessionStore()
events = EventLog(os.environ.get("DB_PATH", "gateway.db"),
                  int(os.environ.get("RETENTION_DAYS", "30")))
limiter = RateLimiter(int(os.environ.get("RATE_PER_MIN", "30")))

app = FastAPI(title="AcousticAcre gateway", version="0.2.0")
if ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["POST"],
                       allow_headers=["content-type", "x-agent-key"])
if (CONTENT_DIR / "clips").exists():
    app.mount("/clips", StaticFiles(directory=CONTENT_DIR / "clips"), name="clips")

if SECRET == "dev-only-change-me":
    log.warning("HMAC_SECRET not set: using a dev secret. Set it before any real use.")


def _check_token(request: Request) -> None:
    """Token in the path (/ussd/<token>) or query (?token=). Path form survives providers that drop query strings."""
    if not TOKEN:
        return
    got = request.path_params.get("token") or request.query_params.get("token")
    if got != TOKEN:
        raise HTTPException(status_code=403, detail="bad token")


def _base_url(request: Request) -> str:
    return os.environ.get("PUBLIC_BASE_URL", str(request.base_url)).rstrip("/")


@app.get("/healthz")
def healthz():
    return {"ok": True, "languages": content.langs, "crops": content.crops,
            "sms_configured": bool(os.environ.get("AT_API_KEY"))}


@app.get("/stats")
def stats():
    """Aggregate counts only (no phone data) for the demo/results slide."""
    return events.summary()


# ------------------------------------------------------------------ USSD --
@app.post("/ussd", response_class=PlainTextResponse)
@app.post("/ussd/{token}", response_class=PlainTextResponse)
def ussd(request: Request, bg: BackgroundTasks,
         sessionId: str = Form(...), phoneNumber: str = Form(...),
         serviceCode: str = Form(""), text: str = Form("")):
    _check_token(request)
    ph = phone_hash(phoneNumber, SECRET)
    if not limiter.allow(ph):
        return "END Too many requests. Please try again later."
    reply, flow = ussd_reply(content, text)
    if reply.startswith("END") and flow.result:
        events.log("ussd", flow.lang, flow.crop, flow.result, ph)
        bg.add_task(send_sms, phoneNumber, sms_text(content, flow.lang, flow.result))
    return reply


# ----------------------------------------------------------------- Voice --
@app.post("/voice")
@app.post("/voice/{token}")
async def voice_cb(request: Request, bg: BackgroundTasks):
    _check_token(request)
    form = await request.form()
    sid = form.get("sessionId", "")
    is_active = str(form.get("isActive", "1"))
    caller = str(form.get("callerNumber", ""))
    digits = str(form.get("dtmfDigits", "") or "").strip()
    base = _base_url(request)

    if is_active == "0":                       # call ended notification
        sessions.drop(sid)
        return PlainTextResponse("")

    s = sessions.get(sid)
    s.phone = caller or s.phone
    first = not s.tokens and not digits
    flow = Flow.replay(content, s.tokens)

    if digits and flow.result is not None:     # post-result menu
        lang = flow.lang
        if digits == voice.POST_RESULT_REPEAT:
            xml = voice.screen_xml(content, flow.screen(), base, TOKEN)
        elif digits == voice.POST_RESULT_SMS:
            if s.phone:
                bg.add_task(send_sms, s.phone, sms_text(content, lang, flow.result))
            xml = voice.say_end(content, lang, "sms_sent", base)
        elif digits == voice.POST_RESULT_HUMAN:
            xml = voice.dial_xml(content, lang, OFFICER, base)
        else:
            xml = voice.say_end(content, lang, "goodbye", base)
        return Response(xml, media_type="text/plain")   # AT examples use text/plain [Verify]

    if digits:
        s.tokens.append(digits[:1])
        flow = Flow.replay(content, s.tokens)

    screen = flow.screen()
    if screen.kind == "result" and not s.finished_logged:
        s.finished_logged = True
        events.log("voice", flow.lang, flow.crop, flow.result, phone_hash(s.phone, SECRET))
    return Response(voice.screen_xml(content, screen, base, TOKEN, first=first), media_type="text/plain")


# ----------------------------------------------------------------- Agent --
@app.post("/agent/send")
async def agent_send(request: Request, bg: BackgroundTasks):
    """Mechanic / extension officer relays a scan result to a farmer by SMS.
    Header X-Agent-Key; JSON {farmer_phone, lang, diagnosis_id}."""
    try:
        who = agent.check_key(request.headers.get("x-agent-key"), AGENT_KEYS)
        payload = await request.json()
        phone, lang, msg = agent.build_message(content, payload, DEFAULT_CC)
    except agent.AgentError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="body must be JSON")
    ph = phone_hash(phone, SECRET)
    if not limiter.allow("agent:" + who):
        raise HTTPException(status_code=429, detail="too many requests")
    events.log("agent", lang, None, payload.get("diagnosis_id"), ph)
    bg.add_task(send_sms, phone, msg)
    return {"queued": True, "lang": lang, "sms": msg, "chars": len(msg)}


# ------------------------------------------------------------------- SMS --
@app.post("/sms/inbound")
@app.post("/sms/inbound/{token}")
async def sms_inbound(request: Request, bg: BackgroundTasks):
    _check_token(request)
    form = await request.form()
    sender = str(form.get("from", ""))
    if sender and limiter.allow(phone_hash(sender, SECRET)):
        bg.add_task(send_sms, sender,
                    f"AcousticAcre: dial {USSD_CODE} to check your cassava for free. "
                    f"{content.ui('en', 'disclaimer')}")
    return PlainTextResponse("")
