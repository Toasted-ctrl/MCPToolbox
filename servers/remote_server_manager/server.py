from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware

from shared.middleware.prometheus import PrometheusMiddleware
from shared.middleware.sanitization import SAFE_EXCEPTIONS, SanitizedErrorMiddleware

from .config import config
from .remote import RemoteError


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

mcp.add_middleware(SanitizedErrorMiddleware(
    safe_exceptions=SAFE_EXCEPTIONS + (RemoteError,)
))

mcp.add_middleware(PrometheusMiddleware())
