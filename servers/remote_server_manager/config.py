import os
from pathlib import Path

from shared.config import BaseConfig


class MCPConfig(BaseConfig):
    ADDITIONAL_VARS = [
        "HOSTS",
    ]

    REQUIRED_VARS = BaseConfig.REQUIRED_VARS + ADDITIONAL_VARS

    def __init__(self) -> None:
        super().__init__(env_path=Path(__file__).parent / ".env")

        # Host inventory in TOML, one table per host. See .env.example and k8s/secrets-example.yaml.
        self.HOSTS: str = os.environ["HOSTS"]
        # Private key (OpenSSH or PEM format) used for every host that has no password
        self.SSH_PRIVATE_KEY: str = os.getenv("SSH_PRIVATE_KEY", "")


config = MCPConfig()
