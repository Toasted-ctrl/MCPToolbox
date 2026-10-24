from prometheus_client import start_http_server

from shared.logger import get_logger

from .config import config
from .server import mcp
from .tools.ssh import (
    create_ssh_session,
    close_ssh_session,
    list_ssh_sessions,
    read_from_ssh_session,
    send_to_ssh_session
)


if __name__ == "__main__":
    log = get_logger(name=config.MCP_NAME)
    log.info(f"Starting Prometheus endpoint at port {config.PROMETHEUS_PORT}")
    start_http_server(
        port=config.PROMETHEUS_PORT,
        addr="0.0.0.0"
    )
    log.info(f"Starting {config.MCP_NAME} at port {config.MCP_PORT}")
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=config.MCP_PORT,
        path="/mcp"
    )