from typing import Union, Callable, TYPE_CHECKING, Type

from pydantic import BaseModel, ValidationError

from fastmessage.common import CustomOutput
from fastmessage.exceptions import MissingCallbackException, MethodValidationError

if TYPE_CHECKING:
    from fastmessage.fastmessage_handler import FastMessage
    from fastmessage.callable_wrapper import CallableWrapper


class MethodValidator:
    """
    a class used to validate results for sending to another method BEFORE sending them
    """

    def __init__(self, fastmessage_handler: 'FastMessage'):
        self._fastmessage_handler = fastmessage_handler

    def _get_callable_wrapper(self, method: Union[str, Callable]) -> 'CallableWrapper':
        input_device = method
        try:
            if callable(method):
                input_device = self._fastmessage_handler._callable_to_input_device[method]

            assert isinstance(input_device, str)
            return self._fastmessage_handler._wrappers[input_device]
        except KeyError:
            raise MissingCallbackException(f'callback {input_device} is not registered')

    def validate_and_return(self, method: Union[str, Callable], **kwargs) -> CustomOutput:
        """
        validates the arguments for the method, and returns it with the right output device

        :param method: the method or input device name to send the arguments to
        :param kwargs: the arguments to the method

        :return: a CustomOutput object, with the right details
        """
        callable_wrapper = self._get_callable_wrapper(method)
        try:
            return CustomOutput(output_device=callable_wrapper.input_device_name,
                                value=callable_wrapper.model(**kwargs))
        except ValidationError as ex:
            raise MethodValidationError(str(ex)) from ex

    def get_model(self, method: Union[str, Callable]) -> Type[BaseModel]:
        """
        return the input model for the method

        :param method: the method (or input device name) to get the model to
        :return: the BaseModel type for that method
        """
        return self._get_callable_wrapper(method).model
