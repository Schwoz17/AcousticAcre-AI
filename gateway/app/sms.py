"""Send SMS through Africa's Talking's REST API using only the standard library."""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

log = logging.getLogger("gateway.sms")

SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"
LIVE_URL = "https://api.africastalking.com/version1/messaging"


def send_sms(to: str, message: str) -> dict | None:
    username = os.environ.get("AT_USERNAME", "sandbox")
    api_key = os.environ.get("AT_API_KEY")
    if not api_key:
        log.warning("AT_API_KEY not set; SMS not sent (%d chars)", len(message))
        return None
    data = {"username": username, "to": to, "message": message}
    if os.environ.get("AT_SMS_FROM"):
        data["from"] = os.environ["AT_SMS_FROM"]
    req = urllib.request.Request(
        SANDBOX_URL if username == "sandbox" else LIVE_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"apiKey": api_key, "Accept": "application/json",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read().decode())
            log.info("SMS sent: %s", body.get("SMSMessageData", {}).get("Message"))
            return body
    except Exception as e:  # never crash a callback over an SMS
        log.error("SMS failed: %s", e)
        return None
