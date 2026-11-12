from prometheus_client import start_http_server

from shared.logger import get_logger

from .config import config
from .server import mcp

# Importing the tool modules registers their tools on `mcp`. Ruff's F401
# (unused import) is disabled for main.py so these aren't removed.
from .tools.ge import get_grand_exchange_item
from .tools.hiscore import (
    disable_player_tracking,
    get_player_current_hiscore,
    get_player_historical_hiscore_item,
    get_players_tracked_hiscores,
    post_tracked_user,
)

if __name__ == "__main__":
    log = get_logger(name=config.MCP_NAME)
    log.info(f"Starting Prometheus endpoint at port {config.PROMETHEUS_PORT}")

    start_http_server(port=config.PROMETHEUS_PORT, addr="0.0.0.0")

    log.info(f"Starting {config.MCP_NAME} at port {config.MCP_PORT}")
    mcp.run(
        transport="streamable-http", host="0.0.0.0", port=config.MCP_PORT, path="/mcp"
    )
