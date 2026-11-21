"""Agent mode (FR-10): a mechanic / extension officer scans with the app, then sends
the result to a farmer's phone by SMS. Framework-free so it can be unit tested.
"""
from __future__ import annotations

import hmac
import re

from .engine import UNCERTAIN, Content, sms_text

E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class AgentError(ValueError):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def check_key(provided: str | None, keys: list[str]) -> str:
    """Returns an agent label (first 6 chars of the key) or raises."""
    if not keys:
        raise AgentError(503, "agent mode disabled: set AGENT_KEYS")
    if provided and any(hmac.compare_digest(provided, k) for k in keys):
        return provided[:6]
    raise AgentError(401, "bad agent key")


def normalise_phone(phone: str, default_cc: str = "234") -> str:
    p = re.sub(r"[\s\-()]", "", phone or "")
    if p.startswith("00"):
        p = "+" + p[2:]
    elif p.startswith("0") and default_cc:      # local Nigerian format 0803... -> +234803...
        p = "+" + default_cc + p[1:]
    elif not p.startswith("+"):
        p = "+" + p
    if not E164.match(p):
        raise AgentError(422, "phone must be a valid number, e.g. +2348031234567")
    return p


def build_message(content: Content, payload: dict, default_cc: str = "234") -> tuple[str, str, str]:
    """payload: {farmer_phone, lang, diagnosis_id}. Returns (phone, lang, sms)."""
    phone = normalise_phone(str(payload.get("farmer_phone", "")), default_cc)
    lang = payload.get("lang") or "en"
    if lang not in content.phrases:
        lang = "en" if "en" in content.phrases else content.langs[0]   # fall back, never fail the farmer
    diag = payload.get("diagnosis_id")
    if diag != UNCERTAIN and diag not in content.diagnoses:
        raise AgentError(422, f"unknown diagnosis_id {diag!r}")
    return phone, lang, sms_text(content, lang, diag)
