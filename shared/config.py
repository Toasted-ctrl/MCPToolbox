import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .logger import get_logger


class BaseConfig:
    """Base configuration class which import the minimum environment variables required to run the MCP.
    To add additional required variables, just use REQUIRED_VARS = BaseConfig.REQUIRED_VARS + ADDITIONAL_VARS: list"""

    REQUIRED_VARS = ["PROMETHEUS_PORT", "MCP_NAME", "MCP_PORT", "APP_VERSION"]

    def __init__(self, env_path: Path | None = None) -> None:
        if env_path:
            load_dotenv(env_path)
        missing = [var for var in self.REQUIRED_VARS if not os.getenv(var)]
        if missing:
            sys.exit(f"Missing environment variables: {', '.join(missing)}")
        log = get_logger(os.environ["MCP_NAME"])
        log.info(f"Setting up config for {os.getenv('MCP_NAME')}")

        self.MCP_NAME: str = os.environ["MCP_NAME"]
        self.MCP_PORT: int = int(os.environ["MCP_PORT"])
        self.PROMETHEUS_PORT: int = int(os.environ["PROMETHEUS_PORT"])
