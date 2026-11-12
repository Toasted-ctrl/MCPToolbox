from typing import Any

import pytest

from shared.errors import NotFoundError
from shared.middleware.sanitization import (
    GENERIC_MESSAGE,
    SAFE_EXCEPTIONS,
    SanitizedErrorMiddleware,
)


def raising(exc: BaseException) -> Any:
    async def call_next(request: object) -> None:
        raise exc

    return call_next


def chained(outer: Exception, cause: Exception) -> Exception:
    """Build `outer` with `cause` attached, as if raised via `raise outer from cause`."""
    try:
        raise outer from cause
    except Exception as exc:
        return exc


async def test_passes_through_result() -> None:
    async def call_next(request: object) -> str:
        return "ok"

    assert await SanitizedErrorMiddleware().on_call_tool(object(), call_next) == "ok"


@pytest.mark.parametrize("exc_cls", SAFE_EXCEPTIONS)
async def test_safe_exceptions_pass_through(exc_cls: type[Exception]) -> None:
    error = exc_cls("user-facing detail")

    with pytest.raises(exc_cls) as exc_info:
        await SanitizedErrorMiddleware().on_call_tool(object(), raising(error))

    assert exc_info.value is error


async def test_unsafe_exception_is_replaced_with_generic_error() -> None:
    error = ConnectionError("db at 10.0.0.5:5432 refused connection")

    with pytest.raises(RuntimeError) as exc_info:
        await SanitizedErrorMiddleware().on_call_tool(object(), raising(error))

    assert str(exc_info.value) == GENERIC_MESSAGE
    assert "10.0.0.5" not in str(exc_info.value)
    # `from None` must hide the original so it can't leak through the traceback.
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


async def test_wrapped_safe_cause_passes_through() -> None:
    # Mimics FastMCP wrapping a tool's exception in ToolError.
    error = chained(Exception("wrapper"), NotFoundError("player not found"))

    with pytest.raises(Exception) as exc_info:
        await SanitizedErrorMiddleware().on_call_tool(object(), raising(error))

    assert exc_info.value is error


async def test_safe_cause_found_deep_in_chain() -> None:
    inner = chained(OSError("middle"), KeyError("missing"))
    error = chained(Exception("outer"), inner)

    with pytest.raises(Exception) as exc_info:
        await SanitizedErrorMiddleware().on_call_tool(object(), raising(error))

    assert exc_info.value is error


async def test_implicit_context_is_also_checked() -> None:
    try:
        try:
            raise ValueError("bad value")
        except ValueError:
            raise Exception("raised while handling")
    except Exception as exc:
        error = exc

    with pytest.raises(Exception) as exc_info:
        await SanitizedErrorMiddleware().on_call_tool(object(), raising(error))

    assert exc_info.value is error


async def test_unsafe_chain_is_sanitized() -> None:
    error = chained(Exception("wrapper"), OSError("/etc/secret not readable"))

    with pytest.raises(RuntimeError, match=GENERIC_MESSAGE):
        await SanitizedErrorMiddleware().on_call_tool(object(), raising(error))


async def test_custom_message_and_safe_exceptions() -> None:
    middleware = SanitizedErrorMiddleware(
        generic_message="Nope.", safe_exceptions=(PermissionError,)
    )

    with pytest.raises(PermissionError):
        await middleware.on_call_tool(object(), raising(PermissionError("denied")))

    # ValueError is safe by default but not in the custom tuple.
    with pytest.raises(RuntimeError, match="Nope."):
        await middleware.on_call_tool(object(), raising(ValueError("bad")))
