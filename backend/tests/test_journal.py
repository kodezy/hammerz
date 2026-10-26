import json
import uuid

import pytest

from app.core.errors import AppError, ErrorCode
from app.modules.journal import Journal


def test_prepare_fsync_then_commit(tmp_path):
    j = Journal(tmp_path, secret=b"k", deployment_id="d")
    j.open()
    rec = {"operation_id": str(uuid.uuid4()), "event": {"type": "AUCTION_CREATED"}}
    j.append_prepare(rec)
    j.append_commit(uuid.UUID(rec["operation_id"]))
    assert j.has_commit(uuid.UUID(rec["operation_id"]))


def test_corrupt_tail_blocks(tmp_path):
    j = Journal(tmp_path, secret=b"k", deployment_id="d")
    j.open()
    rec = {"operation_id": str(uuid.uuid4()), "event": {"type": "AUCTION_CREATED"}}
    j.append_prepare(rec)
    with open(j.journal_path, "ab") as handle:
        handle.write(b"truncated")
    j2 = Journal(tmp_path, secret=b"k", deployment_id="d")
    j2.open()
    assert j2.blocked
    with pytest.raises(AppError) as exc:
        j2.append_prepare({"operation_id": str(uuid.uuid4())})
    assert exc.value.code == ErrorCode.AUDIT_UNAVAILABLE


def test_open_verifies_chain(tmp_path):
    j = Journal(tmp_path, secret=b"secret-key", deployment_id="dep")
    j.open()
    op = uuid.uuid4()
    j.append_prepare({"operation_id": str(op), "event": {"type": "TEST"}})
    j.append_commit(op)
    j2 = Journal(tmp_path, secret=b"secret-key", deployment_id="dep")
    j2.open()
    assert not j2.blocked
    assert j2.has_commit(op)


def test_rewrite_detected(tmp_path):
    j = Journal(tmp_path, secret=b"secret-key", deployment_id="dep")
    j.open()
    op = uuid.uuid4()
    j.append_prepare({"operation_id": str(op)})
    j.append_commit(op)
    lines = j.journal_path.read_text(encoding="utf-8").splitlines()
    line = json.loads(lines[0])
    line["event"] = {"tampered": True}
    with open(j.journal_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(line) + "\n")
        handle.write(lines[1] + "\n")
    j2 = Journal(tmp_path, secret=b"secret-key", deployment_id="dep")
    j2.open()
    assert j2.blocked
