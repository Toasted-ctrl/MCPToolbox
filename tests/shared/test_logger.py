import logging
import sys

import pytest

from shared.logger import get_logger


@pytest.fixture
def logger_name(request: pytest.FixtureRequest) -> str:
    """Loggers are global, so give each test its own name."""
    return f"test.{request.node.name}"


def test_returns_named_logger(logger_name: str) -> None:
    logger = get_logger(logger_name)

    assert logger.name == logger_name
    assert logger.level == logging.DEBUG
    assert logger.propagate is False


def test_respects_custom_level(logger_name: str) -> None:
    logger = get_logger(logger_name, level=logging.WARNING)

    assert logger.level == logging.WARNING
    assert logger.handlers[0].level == logging.WARNING


def test_does_not_duplicate_handlers(logger_name: str) -> None:
    first = get_logger(logger_name)
    second = get_logger(logger_name)

    assert first is second
    assert len(second.handlers) == 1


def test_writes_formatted_message_to_stdout(
    logger_name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    # The handler binds sys.stdout when it's created, so create it inside the test
    # where capsys has already replaced stdout.
    logger = get_logger(logger_name)
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is sys.stdout

    logger.info("hello world")

    out = capsys.readouterr().out
    assert "INFO" in out
    assert "hello world" in out
    assert "Func: test_writes_formatted_message_to_stdout" in out
    assert "Mod: test_logger" in out


def test_messages_below_level_are_dropped(
    logger_name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    logger = get_logger(logger_name, level=logging.WARNING)

    logger.info("should not appear")

    assert capsys.readouterr().out == ""
