import asyncio
import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.core.canon import SCHEMA_VERSION, journal_mac, secret_key_id
from app.core.canon import dumps as canon_dumps
from app.core.errors import AppError, ErrorCode

GENESIS_PREV = "0" * 64
JOURNAL_SCHEMA = 1


class Journal:
    def __init__(self, audit_dir: str | Path, secret: bytes, deployment_id: str) -> None:
        self.audit_dir = Path(audit_dir)
        self.secret = secret
        self.deployment_id = deployment_id
        self.key_id = secret_key_id(secret)
        self.blocked = False
        self._async_lock = asyncio.Lock()
        self._seq = 0
        self._last_hmac = GENESIS_PREV
        self._pending_operation_id: uuid.UUID | None = None
        self.journal_path = self.audit_dir / "journal.jsonl"
        self.manifest_path = self.audit_dir / "manifest.json"
        self.lock_path = self.audit_dir / "journal.lock"

    def open(self, db_has_auctions: bool = False) -> None:
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        missing = not self.manifest_path.exists() or not self.journal_path.exists()
        if missing and db_has_auctions:
            self.blocked = True
            return
        if not self.manifest_path.exists() and not self.journal_path.exists():
            self._write_manifest_genesis()
            self.journal_path.write_text("", encoding="utf-8")
            self._seq = 0
            self._last_hmac = GENESIS_PREV
            self.blocked = False
            return
        if missing:
            self.blocked = True
            return
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if manifest.get("secret_key_id") != self.key_id:
            self.blocked = True
            return
        if manifest.get("deployment_id") != self.deployment_id:
            self.blocked = True
            return
        try:
            self._verify_chain()
        except (json.JSONDecodeError, KeyError, ValueError):
            self.blocked = True

    def _write_manifest_genesis(self) -> None:
        genesis_line = {
            "deployment_id": self.deployment_id,
            "schema_version": JOURNAL_SCHEMA,
            "type": "MANIFEST",
        }
        mac = journal_mac(
            self.secret,
            self.deployment_id,
            self.key_id,
            GENESIS_PREV,
            genesis_line,
        )
        manifest = {
            **genesis_line,
            "secret_key_id": self.key_id,
            "genesis_hmac": mac,
        }
        self.manifest_path.write_text(
            json.dumps(manifest, separators=(",", ":")),
            encoding="utf-8",
        )

    def _verify_chain(self) -> None:
        prev = GENESIS_PREV
        seq = 0
        pending: uuid.UUID | None = None
        text = self.journal_path.read_text(encoding="utf-8")
        if not text.strip():
            self._seq = 0
            self._last_hmac = GENESIS_PREV
            self._pending_operation_id = None
            self.blocked = False
            return
        for raw_line in text.splitlines():
            if not raw_line.strip():
                continue
            line = json.loads(raw_line)
            body = {k: v for k, v in line.items() if k != "hmac"}
            expected = journal_mac(
                self.secret,
                self.deployment_id,
                self.key_id,
                prev,
                body,
            )
            if not hmac_compare(expected, line.get("hmac", "")):
                raise ValueError("hmac mismatch")
            seq = int(line["seq"])
            prev = line["hmac"]
            line_type = line["type"]
            op_id = uuid.UUID(str(line["operation_id"]))
            if line_type == "PREPARE":
                pending = op_id
            elif line_type == "COMMIT":
                if pending != op_id:
                    raise ValueError("commit without prepare")
                pending = None
            elif line_type == "ABORT":
                pending = None
        self._seq = seq
        self._last_hmac = prev
        self._pending_operation_id = pending
        self.blocked = False

    @contextmanager
    def acquire(self, timeout: float = 5.0):
        lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        try:
            import time

            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise AppError(
                            503,
                            ErrorCode.AUDIT_UNAVAILABLE,
                            "Audit journal lock timeout",
                        )
                    time.sleep(0.05)
            yield
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    async def run_locked(self, fn):
        async with self._async_lock:

            def _run():
                with self.acquire():
                    return fn()

            return await asyncio.to_thread(_run)

    def _ensure_writable(self) -> None:
        if self.blocked:
            raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal unavailable")
        if self._pending_operation_id is not None:
            raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal has pending prepare")

    def append_prepare(self, record: dict[str, Any]) -> None:
        self._ensure_writable()
        operation_id = uuid.UUID(str(record["operation_id"]))
        line: dict[str, Any] = {
            "deployment_id": self.deployment_id,
            "operation_id": str(operation_id),
            "prev": self._last_hmac,
            "schema_version": SCHEMA_VERSION,
            "seq": self._seq + 1,
            "type": "PREPARE",
        }
        if "event" in record:
            line["event"] = record["event"]
        if "fingerprint" in record:
            line["fingerprint"] = record["fingerprint"]
        mac = journal_mac(
            self.secret,
            self.deployment_id,
            self.key_id,
            self._last_hmac,
            line,
        )
        line["hmac"] = mac
        with self.acquire():
            self._append_line(line)
            self._seq += 1
            self._last_hmac = mac
            self._pending_operation_id = operation_id

    def append_commit(self, operation_id: uuid.UUID) -> None:
        if self.blocked:
            raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "Audit journal unavailable")
        if self._pending_operation_id != operation_id:
            raise AppError(503, ErrorCode.AUDIT_UNAVAILABLE, "No matching prepare for commit")
        line: dict[str, Any] = {
            "deployment_id": self.deployment_id,
            "operation_id": str(operation_id),
            "prev": self._last_hmac,
            "schema_version": SCHEMA_VERSION,
            "seq": self._seq + 1,
            "type": "COMMIT",
        }
        mac = journal_mac(
            self.secret,
            self.deployment_id,
            self.key_id,
            self._last_hmac,
            line,
        )
        line["hmac"] = mac
        with self.acquire():
            self._append_line(line)
            self._seq += 1
            self._last_hmac = mac
            self._pending_operation_id = None

    def append_abort(self, operation_id: uuid.UUID) -> None:
        if self.blocked:
            return
        if self._pending_operation_id != operation_id:
            return
        line: dict[str, Any] = {
            "deployment_id": self.deployment_id,
            "operation_id": str(operation_id),
            "prev": self._last_hmac,
            "schema_version": SCHEMA_VERSION,
            "seq": self._seq + 1,
            "type": "ABORT",
        }
        mac = journal_mac(
            self.secret,
            self.deployment_id,
            self.key_id,
            self._last_hmac,
            line,
        )
        line["hmac"] = mac
        with self.acquire():
            self._append_line(line)
            self._seq += 1
            self._last_hmac = mac
            self._pending_operation_id = None

    def _append_line(self, line: dict[str, Any]) -> None:
        with open(self.journal_path, "a", encoding="utf-8") as handle:
            handle.write(canon_dumps(line).decode("utf-8"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

    def has_commit(self, operation_id: uuid.UUID) -> bool:
        if not self.journal_path.exists():
            return False
        op = str(operation_id)
        for raw_line in self.journal_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            line = json.loads(raw_line)
            if line.get("type") == "COMMIT" and line.get("operation_id") == op:
                return True
        return False

    def pending_prepare(self) -> dict | None:
        if self._pending_operation_id is None:
            return None
        return {"operation_id": str(self._pending_operation_id)}


def hmac_compare(a: str, b: str) -> bool:
    import hmac as hm

    return hm.compare_digest(a, b)
