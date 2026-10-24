from collections.abc import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .logger import get_logger


log = get_logger()


@contextmanager
def get_db_session(db_url: str) -> Generator[Session]:
    """Function that will yield a database session.
    Rollback will happen automatically upon detection of issues.
    Does not autocommit or autoflush, committing and flushing will
    require manual actions."""
    engine = create_engine(url=db_url, echo=False)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False
    )
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        log.exception(f"Error during database session: {str(e)}. Rolling back changes.")
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()