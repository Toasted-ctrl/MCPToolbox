from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware

from shared.middleware.prometheus import PrometheusMiddleware
from shared.middleware.sanitization import SanitizedErrorMiddleware

from .config import config


mcp = FastMCP(
    name=config.MCP_NAME
)

mcp.add_middleware(LoggingMiddleware(
    include_payloads=True
))

mcp.add_middleware(ErrorHandlingMiddleware(
    include_traceback=False,
    transform_errors=True
))

mcp.add_middleware(SanitizedErrorMiddleware())

mcp.add_middleware(PrometheusMiddleware())