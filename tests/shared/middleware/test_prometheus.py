from types import SimpleNamespace

import pytest
from prometheus_client import REGISTRY

from shared.middleware.prometheus import PrometheusMiddleware


def make_context(tool: str) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(name=tool))


def calls(tool: str, status: str) -> float:
    value = REGISTRY.get_sample_value(
        "mcp_tool_calls_total", {"tool": tool, "status": status}
    )
    return value or 0.0


def duration_count(tool: str) -> float:
    value = REGISTRY.get_sample_value("mcp_tool_duration_seconds_count", {"tool": tool})
    return value or 0.0


# The metrics are module-level globals shared across tests, so each test uses a
# unique tool name to keep the counts independent.


async def test_counts_successful_call() -> None:
    tool = "prom_success_tool"

    async def call_next(context: SimpleNamespace) -> str:
        return "result"

    result = await PrometheusMiddleware().on_call_tool(make_context(tool), call_next)

    assert result == "result"
    assert calls(tool, "success") == 1
    assert calls(tool, "error") == 0
    assert duration_count(tool) == 1


async def test_counts_failed_call_and_reraises() -> None:
    tool = "prom_error_tool"

    async def call_next(context: SimpleNamespace) -> str:
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        await PrometheusMiddleware().on_call_tool(make_context(tool), call_next)

    assert calls(tool, "error") == 1
    assert calls(tool, "success") == 0
    assert duration_count(tool) == 1


async def test_counts_accumulate_per_tool() -> None:
    tool = "prom_repeat_tool"
    middleware = PrometheusMiddleware()

    async def call_next(context: SimpleNamespace) -> None:
        return None

    for _ in range(3):
        await middleware.on_call_tool(make_context(tool), call_next)

    assert calls(tool, "success") == 3
    assert duration_count(tool) == 3
