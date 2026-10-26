def test_live_ok(live_client):
    r = live_client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
