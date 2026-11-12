from pathlib import Path

import pytest
from sqlalchemy import text

from shared.db import get_db_session


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    # File-backed so data survives across sessions (in-memory SQLite is per connection).
    url = f"sqlite:///{tmp_path / 'test.db'}"
    with get_db_session(db_url=url) as db:
        db.execute(text("CREATE TABLE items (name TEXT)"))
        db.commit()
    return url


def count_items(db_url: str) -> int:
    with get_db_session(db_url=db_url) as db:
        return db.execute(text("SELECT COUNT(*) FROM items")).scalar_one()


def test_yields_working_session(db_url: str) -> None:
    with get_db_session(db_url=db_url) as db:
        assert db.execute(text("SELECT 1")).scalar_one() == 1


def test_committed_changes_persist(db_url: str) -> None:
    with get_db_session(db_url=db_url) as db:
        db.execute(text("INSERT INTO items VALUES ('a')"))
        db.commit()

    assert count_items(db_url) == 1


def test_does_not_autocommit(db_url: str) -> None:
    with get_db_session(db_url=db_url) as db:
        db.execute(text("INSERT INTO items VALUES ('a')"))

    assert count_items(db_url) == 0


def test_rolls_back_and_reraises_on_error(db_url: str) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with get_db_session(db_url=db_url) as db:
            db.execute(text("INSERT INTO items VALUES ('a')"))
            db.flush()
            raise RuntimeError("boom")

    assert count_items(db_url) == 0


def test_session_is_closed_after_use(db_url: str) -> None:
    with get_db_session(db_url=db_url) as db:
        db.execute(text("INSERT INTO items VALUES ('a')"))
        assert db.in_transaction()

    assert not db.in_transaction()
