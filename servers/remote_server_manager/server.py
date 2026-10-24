from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware, default_serializer
from typing import Any
import json

from shared.middleware.prometheus import PrometheusMiddleware
from shared.middleware.sanitization import SanitizedErrorMiddleware

from .config import config


# Payload keys whose values must never end up in the logs
_SENSITIVE_KEYS = {"password"}


def _mask_sensitive(data: Any) -> Any:
    """Recursively replace the values of sensitive keys with a placeholder."""
    if isinstance(data, dict):
        return {
            key: "***" if key in _SENSITIVE_KEYS else _mask_sensitive(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [_mask_sensitive(item) for item in data]
    return data


def _masked_serializer(data: Any) -> str:
    """Serializes the payload like FastMCP does, with sensitive values masked."""
    return json.dumps(_mask_sensitive(json.loads(default_serializer(data))))


mcp = FastMCP(
    name=config.MCP_NAME
)

mcp.add_middleware(LoggingMiddleware(
    include_payloads=True,
    payload_serializer=_masked_serializer
))

mcp.add_middleware(ErrorHandlingMiddleware(
    include_traceback=False,
    transform_errors=True
))

mcp.add_middleware(SanitizedErrorMiddleware())

mcp.add_middleware(PrometheusMiddleware())