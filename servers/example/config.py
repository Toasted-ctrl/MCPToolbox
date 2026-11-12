from pathlib import Path

from shared.config import BaseConfig


class MCPConfig(BaseConfig):
    def __init__(self):
        super().__init__(env_path=Path(__file__).parent / ".env")


config = MCPConfig()
