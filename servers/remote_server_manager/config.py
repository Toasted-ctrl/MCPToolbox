from pathlib import Path
import os

from shared.config import BaseConfig


def _split(value: str, separator: str) -> list[str]:
    """Splits a separated environment variable into a list, dropping empty entries."""
    return [item.strip() for item in value.split(separator) if item.strip()]


class MCPConfig(BaseConfig):

    ADDITIONAL_VARS = [
        "PG_DIALECT",
        "PG_DRIVER",
        "PG_PORT",
        "PG_HOSTNAME",
        "PG_DATABASE",
        "PG_USER",
        "PG_PASSWORD",
    ]

    REQUIRED_VARS = BaseConfig.REQUIRED_VARS + ADDITIONAL_VARS

    def __init__(self):
        super().__init__(env_path=Path(__file__).parent / ".env")

        self.DB_DIALECT: str = os.getenv("PG_DIALECT")
        self.DB_DRIVER: str = os.getenv("PG_DRIVER")
        self.DB_PORT: str = os.getenv("PG_PORT")
        self.DB_HOSTNAME: str = os.getenv("PG_HOSTNAME")
        self.DB_DATABASE: str = os.getenv("PG_DATABASE")
        self.DB_USERNAME: str = os.getenv("PG_USER")
        self.DB_PASSWORD: str = os.getenv("PG_PASSWORD")

        # Command restrictions, see restrictions.py for the available groups
        self.ENABLED_RESTRICTIONS: list[str] = _split(os.getenv("ENABLED_RESTRICTIONS", ""), ",")
        self.DISABLED_RESTRICTIONS: list[str] = _split(os.getenv("DISABLED_RESTRICTIONS", ""), ",")
        # One regex per line, since regexes can contain commas
        self.EXTRA_FORBIDDEN_PATTERNS: list[str] = _split(os.getenv("EXTRA_FORBIDDEN_PATTERNS", ""), "\n")

        # IP addresses / CIDR ranges sessions may be created with. When empty, all hosts are allowed.
        self.ALLOWED_HOSTS: list[str] = _split(os.getenv("ALLOWED_HOSTS", ""), ",")

    @property
    def DB_URL(self) -> str:
        return (
            f"{self.DB_DIALECT}+{self.DB_DRIVER}://"
            f"{self.DB_USERNAME}:{self.DB_PASSWORD}@"
            f"{self.DB_HOSTNAME}:{self.DB_PORT}/{self.DB_DATABASE}"
        )

config = MCPConfig()