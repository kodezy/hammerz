import pytest


@pytest.mark.skip(reason="Requires PostgreSQL and Met API mocks for full seed")
def test_seed_idempotent_opening_balance():
    pass
