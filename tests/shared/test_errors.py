import pytest

from shared.errors import ConfigurationError, NotFoundError


@pytest.mark.parametrize("error_cls", [ConfigurationError, NotFoundError])
def test_custom_errors_are_exceptions(error_cls: type[Exception]) -> None:
    with pytest.raises(error_cls, match="details"):
        raise error_cls("details")


def test_custom_errors_are_distinct() -> None:
    assert not issubclass(NotFoundError, ConfigurationError)
    assert not issubclass(ConfigurationError, NotFoundError)
