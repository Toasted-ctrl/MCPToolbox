from prometheus_client import start_http_server

from shared.logger import get_logger

from .config import config
from .server import mcp
from .tools.hosts import list_hosts
from .tools.services import (
    get_service_status,
    list_services,
    read_service_logs,
    restart_service
)
from .tools.system import (
    get_system_info,
    list_processes
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
