import os
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from shared.config import BaseConfig

VALID_ENV = {
    "MCP_NAME": "test-mcp",
    "MCP_PORT": "8000",
    "PROMETHEUS_PORT": "9000",
    "APP_VERSION": "1.2.3",
}


@pytest.fixture(autouse=True)
def clean_env() -> Iterator[None]:
    """Start every test with an empty environment and restore it afterwards,
    including anything load_dotenv writes to os.environ."""
    with mock.patch.dict(os.environ, clear=True):
        yield


def test_loads_required_vars_from_environment() -> None:
    os.environ.update(VALID_ENV)

    config = BaseConfig()

    assert config.MCP_NAME == "test-mcp"
    assert config.MCP_PORT == 8000
    assert config.PROMETHEUS_PORT == 9000


def test_loads_required_vars_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("".join(f"{k}={v}\n" for k, v in VALID_ENV.items()))

    config = BaseConfig(env_path=env_file)

    assert config.MCP_NAME == "test-mcp"
    assert config.MCP_PORT == 8000


def test_environment_takes_precedence_over_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("".join(f"{k}={v}\n" for k, v in VALID_ENV.items()))
    os.environ["MCP_NAME"] = "from-environment"

    config = BaseConfig(env_path=env_file)

    assert config.MCP_NAME == "from-environment"


def test_exits_listing_all_missing_vars() -> None:
    os.environ.update({"MCP_NAME": "test-mcp", "MCP_PORT": "8000"})

    with pytest.raises(SystemExit) as exc_info:
        BaseConfig()

    message = str(exc_info.value)
    assert "PROMETHEUS_PORT" in message
    assert "APP_VERSION" in message
    assert "MCP_NAME" not in message


def test_empty_var_counts_as_missing() -> None:
    os.environ.update(VALID_ENV | {"APP_VERSION": ""})

    with pytest.raises(SystemExit, match="APP_VERSION"):
        BaseConfig()


def test_non_integer_port_raises() -> None:
    os.environ.update(VALID_ENV | {"MCP_PORT": "not-a-port"})

    with pytest.raises(ValueError):
        BaseConfig()


def test_subclass_can_extend_required_vars() -> None:
    class ExtendedConfig(BaseConfig):
        REQUIRED_VARS = BaseConfig.REQUIRED_VARS + ["EXTRA_VAR"]

    os.environ.update(VALID_ENV)

    with pytest.raises(SystemExit, match="EXTRA_VAR"):
        ExtendedConfig()
