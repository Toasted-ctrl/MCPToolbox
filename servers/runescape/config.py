import os
from pathlib import Path

from shared.config import BaseConfig


class MCPConfig(BaseConfig):
    ADDITIONAL_VARS = [
        "PG_DIALECT",
        "PG_DRIVER",
        "PG_PORT",
        "PG_HOSTNAME",
        "PG_DATABASE",
        "PG_USER",
        "PG_PASSWORD",
        "RUNESCAPE_GE_ITEM_ID_URL",
        "RUNESCAPE_HISCORE_URL",
    ]

    REQUIRED_VARS = BaseConfig.REQUIRED_VARS + ADDITIONAL_VARS

    def __init__(self) -> None:
        super().__init__(env_path=Path(__file__).parent / ".env")

        self.DB_DIALECT: str = os.environ["PG_DIALECT"]
        self.DB_DRIVER: str = os.environ["PG_DRIVER"]
        self.DB_PORT: str = os.environ["PG_PORT"]
        self.DB_HOSTNAME: str = os.environ["PG_HOSTNAME"]
        self.DB_DATABASE: str = os.environ["PG_DATABASE"]
        self.DB_USERNAME: str = os.environ["PG_USER"]
        self.DB_PASSWORD: str = os.environ["PG_PASSWORD"]

        self.RS_GE_LINK: str = os.environ["RUNESCAPE_GE_ITEM_ID_URL"]
        self.RS_HS_LINK: str = os.environ["RUNESCAPE_HISCORE_URL"]

    @property
    def DB_URL(self) -> str:
        return (
            f"{self.DB_DIALECT}+{self.DB_DRIVER}://"
            f"{self.DB_USERNAME}:{self.DB_PASSWORD}@"
            f"{self.DB_HOSTNAME}:{self.DB_PORT}/{self.DB_DATABASE}"
        )


config = MCPConfig()
