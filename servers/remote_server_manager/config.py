from pathlib import Path
import os

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

    @property
    def DB_URL(self) -> str:
        return (
            f"{self.DB_DIALECT}+{self.DB_DRIVER}://"
            f"{self.DB_USERNAME}:{self.DB_PASSWORD}@"
            f"{self.DB_HOSTNAME}:{self.DB_PORT}/{self.DB_DATABASE}"
        )

config = MCPConfig()