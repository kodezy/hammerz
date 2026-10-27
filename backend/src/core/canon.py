import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

JOURNAL_DOMAIN = "hammerz:journal:v1"
EVENT_DOMAIN = "hammerz:event:v1"
SCHEMA_VERSION = 1


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, uuid.UUID):
        return str(value).lower()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        utc = value.astimezone(UTC)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, float):
        raise TypeError("float not allowed in canonical JSON")
    return value


def dumps(obj: dict) -> bytes:
    normalized = _normalize(obj)
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def secret_key_id(secret: bytes) -> str:
    return hashlib.sha256(secret).hexdigest()[:8]


def journal_mac(secret: bytes, deployment_id: str, key_id: str, prev_hex: str, line_without_hmac: dict) -> str:
    payload = dumps(line_without_hmac)
    msg = f"{JOURNAL_DOMAIN}|{deployment_id}|{key_id}|{prev_hex}|".encode() + payload
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def event_mac(secret: bytes, deployment_id: str, key_id: str, prev_hex: str, payload: dict) -> str:
    body = dumps(payload)
    msg = f"{EVENT_DOMAIN}|{deployment_id}|{key_id}|{prev_hex}|".encode() + body
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def request_fingerprint(method: str, path: str, body: dict | None) -> str:
    canonical = {"body": body or {}, "method": method.upper(), "path": path}
    return hashlib.sha256(dumps(canonical)).hexdigest()
