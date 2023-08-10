import logging
from typing import Callable, Any, TypeVar

from fastmessage.exceptions import UnnamedCallableException

_logger = logging.getLogger('fastmessage')

_CALLABLE_TYPE = TypeVar('_CALLABLE_TYPE', bound=Callable[..., Any])


def _get_callable_name(callback: _CALLABLE_TYPE) -> str:
    try:
        return getattr(callback, "__name__")
    except AttributeError as ex:
        raise UnnamedCallableException(f"Callable {repr(callback)} doesn't have a name") from ex
