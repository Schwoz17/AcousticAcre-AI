"""Session state and privacy-preserving event log.

Raw phone numbers are never stored: only HMAC-SHA256(phone, server secret).
"""
from __future__ import annotations

import hashlib
import hmac
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


def phone_hash(phone: str, secret: str) -> str:
    return hmac.new(secret.encode(), phone.strip().encode(), hashlib.sha256).hexdigest()


@dataclass
class VoiceSession:
    tokens: list[str] = field(default_factory=list)
    phone: str = ""                 # kept in memory only for the SMS / call-back during the call
    finished_logged: bool = False
    updated: float = field(default_factory=time.time)


class SessionStore:
    """In-memory voice sessions (USSD needs none: AT resends the full path)."""

    def __init__(self, ttl_s: int = 900):
        self.ttl = ttl_s
        self._d: dict[str, VoiceSession] = {}
        self._lock = threading.Lock()

    def get(self, sid: str) -> VoiceSession:
        with self._lock:
            self._expire()
            s = self._d.setdefault(sid, VoiceSession())
            s.updated = time.time()
            return s

    def drop(self, sid: str) -> None:
        with self._lock:
            self._d.pop(sid, None)

    def _expire(self) -> None:
        now = time.time()
        for k in [k for k, v in self._d.items() if now - v.updated > self.ttl]:
            del self._d[k]


class EventLog:
    def __init__(self, path: str, retention_days: int = 30):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY, ts REAL, channel TEXT, lang TEXT, crop TEXT,
            result TEXT, phone_hash TEXT)""")
        self.db.execute("DELETE FROM events WHERE ts < ?", (time.time() - retention_days * 86400,))
        self.db.commit()

    def log(self, channel: str, lang: str | None, crop: str | None, result: str | None, ph: str) -> None:
        with self._lock:
            self.db.execute("INSERT INTO events(ts,channel,lang,crop,result,phone_hash) VALUES(?,?,?,?,?,?)",
                            (time.time(), channel, lang, crop, result, ph))
            self.db.commit()

    def summary(self) -> dict:
        with self._lock:
            rows = self.db.execute(
                "SELECT channel, result, COUNT(*) FROM events GROUP BY channel, result").fetchall()
        return {"counts": [{"channel": c, "result": r, "n": n} for c, r, n in rows]}


class RateLimiter:
    def __init__(self, per_minute: int = 30):
        self.n = per_minute
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.n:
                return False
            q.append(now)
            return True
