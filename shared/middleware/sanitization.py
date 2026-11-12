from fastmcp.server.middleware import Middleware

from ..errors import NotFoundError

SAFE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ValueError,
    TypeError,
    KeyError,
    NotImplementedError,
    NotFoundError,
)

GENERIC_MESSAGE = "An internal error occured. Please try again later."


class SanitizedErrorMiddleware(Middleware):
    """
    Sits between ErrorHandlingMiddleware and tool execution.

    - Exceptions in SAFE_EXCEPTIONS pass through unchanged.
    - Everything else is replaced with a generic RuntimeError
    so that database details, file paths, hostnames, etc.
    never reach the client.
    """

    def __init__(
        self,
        *,
        generic_message: str = GENERIC_MESSAGE,
        safe_exceptions: tuple[type[Exception], ...] | None = None,
    ):
        self.generic_message = generic_message
        self.safe_exceptions = safe_exceptions or SAFE_EXCEPTIONS

    async def on_call_tool(self, request, call_next):
        return await self._safe_call(call_next, request)

    async def _safe_call(self, call_next, request):
        try:
            return await call_next(request)
        except self.safe_exceptions:
            raise
        except Exception as exc:
            if self._is_safe_cause(exc):
                raise
            raise RuntimeError(self.generic_message) from None

    def _is_safe_cause(self, exc: Exception) -> bool:
        """Walk the exception chain looking for a safe root cause."""

        # NOTE: This step is required, as FastMCP wraps errors in ToolError.
        # We'd never find the true error, and allowing ToolError as safe would just mean we're passing
        # through every error again.

        cause = exc.__cause__ or exc.__context__
        while cause is not None:
            if isinstance(cause, self.safe_exceptions):
                return True
            cause = cause.__cause__ or cause.__context__
        return False
