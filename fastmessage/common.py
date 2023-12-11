import logging
from dataclasses import dataclass
from typing import Callable, Any, TypeVar, Union

from fastmessage.exceptions import UnnamedCallableException

_logger = logging.getLogger('fastmessage')

_CALLABLE_TYPE = TypeVar('_CALLABLE_TYPE', bound=Callable[..., Any])


def get_callable_name(named_callable: _CALLABLE_TYPE) -> str:
    """
    tries to return a callable name

    :param named_callable: the callable to get the name for

    :return: the name of the callable, or raises UnnamedCallableException
    """
    try:
        return getattr(named_callable, "__name__")
    except AttributeError as ex:
        raise UnnamedCallableException(f"Callable {repr(named_callable)} doesn't have a name") from ex


class InputDeviceName(str):
    """
    a place holder class for input_device name
    """
    pass


class MultipleReturnValues(list):
    """
    a value that indicates that multiple output values should be returned
    """
    pass


@dataclass
class CustomOutput:
    """
    a result that contains the output device name to send the value to
    """
    output_device: str
    value: Any


class OtherMethodOutput:
    """
    a result that contains the other method to send the result to
    """

    def __init__(self, method: Union[str, Callable], **kwargs):
        self.method = method
        self.kwargs = kwargs
