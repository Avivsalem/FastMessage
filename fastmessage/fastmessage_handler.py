import asyncio
from asyncio import AbstractEventLoop
from typing import Optional, Callable, Dict, List, Union, Iterable

from pydantic import ValidationError

from fastmessage.callable_wrapper import CallableWrapper
from fastmessage.common import _CALLABLE_TYPE, get_callable_name
from fastmessage.exceptions import DuplicateCallbackException, MissingCallbackException
from messageflux import InputDevice
from messageflux.iodevices.base import InputDeviceManager, OutputDeviceManager
from messageflux.iodevices.base.common import MessageBundle
from messageflux.pipeline_service import PipelineHandlerBase, PipelineResult, PipelineService


class _DefaultClass(str):
    pass


_DEFAULT = _DefaultClass()


class FastMessage(PipelineHandlerBase):
    def __init__(self,
                 default_output_device: Optional[str] = None,
                 validation_error_handler: Optional[Callable[
                     [InputDevice, MessageBundle, ValidationError],
                     Optional[Union[PipelineResult, Iterable[PipelineResult]]]]] = None):
        """

        :param default_output_device: an optional default output device to send callback results to,
        unless mapped otherwise
        :param validation_error_handler: an optional handler that will be called on validation errors,
        in order to give the user a chance to handle them gracefully
        """
        self._default_output_device = default_output_device
        self._validation_error_handler = validation_error_handler
        self._wrappers: Dict[str, CallableWrapper] = {}
        self._callable_to_input_device: Dict[Callable, str] = {}
        self._event_loop_cache: Optional[AbstractEventLoop] = None

    @property
    def event_loop(self) -> AbstractEventLoop:
        """
        the event loop used for running async functions (lazy initialized)
        """
        if self._event_loop_cache is None:
            self._event_loop_cache = asyncio.new_event_loop()

        return self._event_loop_cache

    @property
    def input_devices(self) -> List[str]:
        """
        returns all the input device names that has callbacks
        """
        return list(self._wrappers.keys())

    def register_validation_error_handler(self,
                                          handler: Callable[
                                              [InputDevice, MessageBundle, ValidationError],
                                              Optional[PipelineResult]]):
        """
        registers optional handler that will be called on validation errors,
        in order to give the user a chance to handle them gracefully
        :param handler: the handler to register
        """
        self._validation_error_handler = handler

    def register_callback(self,
                          callback: _CALLABLE_TYPE,
                          input_device: str = _DEFAULT,
                          output_device: Optional[str] = _DEFAULT):
        """
        registers a callback to a device

        :param callback: the callback to register
        :param input_device: the input device to register the callback to
        :param output_device:  optional output device to route the return value of the callback to.
        None means no output routing.
        if callback returns None, no routing will be made even if 'output_device' is not None
        """
        if input_device is _DEFAULT:
            input_device = get_callable_name(callback)

        if input_device in self._wrappers:
            raise DuplicateCallbackException(f"Can't register more than one callback on device '{input_device}'")

        if output_device is _DEFAULT:
            output_device = self._default_output_device

        self._callable_to_input_device[callback] = input_device
        self._wrappers[input_device] = CallableWrapper(fastmessage_handler=self,
                                                       wrapped_callable=callback,
                                                       input_device_name=input_device,
                                                       output_device_name=output_device)

    def map(self,
            input_device: str = _DEFAULT,
            output_device: Optional[str] = _DEFAULT) -> Callable[[_CALLABLE_TYPE], _CALLABLE_TYPE]:
        """
        this is the decorator method

        :param input_device: the input device to register the decorated method on
        :param output_device: optional output device to route the return value of the callback to.
        if callback returns None, no routing will be made even if 'output_device' is not None
        None means no output routing
        """

        def _register_callback_decorator(callback: _CALLABLE_TYPE) -> _CALLABLE_TYPE:
            self.register_callback(callback=callback,
                                   input_device=input_device,
                                   output_device=output_device)
            return callback

        return _register_callback_decorator

    def handle_message(self,
                       input_device: InputDevice,
                       message_bundle: MessageBundle) -> Optional[Union[PipelineResult, Iterable[PipelineResult]]]:
        callback_wrapper = self._wrappers.get(input_device.name)
        if callback_wrapper is None:
            raise MissingCallbackException(f"No callback registered for device '{input_device.name}'")
        try:
            return callback_wrapper(input_device=input_device, message_bundle=message_bundle)
        except ValidationError as ve:
            if self._validation_error_handler is None:
                raise

            return self._validation_error_handler(input_device, message_bundle, ve)

    def create_service(self, *,
                       input_device_manager: InputDeviceManager,
                       input_device_names: Optional[Union[List[str], str]] = None,
                       output_device_manager: Optional[OutputDeviceManager] = None,
                       **kwargs) -> PipelineService:
        """
        creates a PipelineService, with this FastMessage object as its handler

        :param input_device_manager: the input device manager to read items from
        :param input_device_names: Optional. the list of input device names to read from
        (defaults to all the registered mappings)
        :param output_device_manager: Optional. the output device manager to use
        :param **kwargs: passed to PipelineService __init__ as is
        :return: the created PipelineService
        """
        if input_device_names is None:
            input_device_names = self.input_devices

        return PipelineService(input_device_manager=input_device_manager,
                               input_device_names=input_device_names,
                               pipeline_handler=self,
                               output_device_manager=output_device_manager,
                               **kwargs)

    def shutdown(self):
        if self._event_loop_cache is not None:
            self._event_loop_cache.close()
            self._event_loop_cache = None
