from sqlalchemy import inspect


def test_migrate_creates_users(engine):
    names = inspect(engine).get_table_names()
    assert "users" in names
    assert "wallet_ledger" in names
    assert "receipts" in names
    assert "idempotency_requests" in names
