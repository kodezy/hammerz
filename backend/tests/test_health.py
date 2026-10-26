def test_live_ok(live_client):
    r = live_client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_ok_when_journal_open(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_503_when_journal_blocked(tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.modules.journal import Journal

    monkeypatch.setattr("app.api.health.check_database", lambda: True)
    audit_dir = tmp_path / "broken"
    audit_dir.mkdir()
    (audit_dir / "journal.jsonl").write_text("{not valid json\n", encoding="utf-8")
    (audit_dir / "manifest.json").write_text("{}", encoding="utf-8")
    journal = Journal(audit_dir, secret=b"test-hmac-secret", deployment_id="hammerz-test")
    journal.open()
    assert journal.blocked

    from app.main import create_app
    from fastapi.testclient import TestClient

    monkeypatch.setenv("AUDIT_DIR", str(audit_dir))
    get_settings.cache_clear()
    application = create_app()
    application.state.journal = journal
    with TestClient(application) as c:
        r = c.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["code"] == "AUDIT_UNAVAILABLE"
    get_settings.cache_clear()
