class ConfigurationError(Exception):
    """Raised when application configuration is invalid."""

    pass


class NotFoundError(Exception):
    """Raised when a record cannot be found."""

    pass
