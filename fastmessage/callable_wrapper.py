import inspect
import json
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union, Iterable, Generator, AsyncGenerator, TYPE_CHECKING

import itertools
from pydantic import BaseModel, parse_raw_as, create_model, Extra
from pydantic.config import get_config
from pydantic.typing import get_all_type_hints

from fastmessage.common import _CALLABLE_TYPE, _get_callable_name, _logger
from fastmessage.exceptions import NotAllowedParamKindException, SpecialDefaultValueException
from messageflux import InputDevice
from messageflux.iodevices.base.common import MessageBundle, Message
from messageflux.pipeline_service import PipelineResult

if TYPE_CHECKING:
    from fastmessage.fastmessage_handler import FastMessage


@dataclass
class _ParamInfo:
    annotation: Any
    default: Any


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
class FastMessageOutput:
    """
    a result that contains the output device name to send the value to
    """
    output_device: str
    value: Any


class CallableWrapper:
    """
    a helper class that wraps a callable
    """

    def __init__(self, *,
                 fastmessage_handler: 'FastMessage',
                 callback: _CALLABLE_TYPE,
                 input_device: str,
                 output_device: Optional[str] = None):
        self._callback = callback
        self._fastmessage_handler = fastmessage_handler
        self._input_device = input_device
        self._output_device = output_device
        self._special_params: Dict[str, _ParamInfo] = dict()
        self._params: Dict[str, _ParamInfo] = dict()
        self._is_async = inspect.iscoroutinefunction(callback)
        self._is_async_gen = inspect.isasyncgenfunction(callback)

        type_hints = get_all_type_hints(self._callback)
        extra = Extra.ignore
        for param_name, param in inspect.signature(self._callback).parameters.items():
            if param.kind in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL):
                raise NotAllowedParamKindException(
                    f"param '{param_name}' is of '{param.kind}' kind. this is now allowed")

            if param.kind == param.VAR_KEYWORD:  # there's **kwargs param
                extra = Extra.allow
                continue

            annotation = Any if param.annotation is param.empty else type_hints[param_name]
            default = ... if param.default is param.empty else param.default

            param_info = _ParamInfo(annotation=annotation, default=default)

            if param_info.annotation in (MessageBundle, Message, InputDeviceName,
                                         Optional[MessageBundle], Optional[Message], Optional[InputDeviceName]):
                if param_info.default is not ...:
                    raise SpecialDefaultValueException(
                        f"param '{param_name}' is of special type '{param.annotation.__name__}' "
                        f"but has a default value")
                self._special_params[param_name] = param_info

            else:
                self._params[param_name] = param_info

        self._model = None
        if self._params:
            model_name = self._get_model_name()
            model_params: Dict[str, Any] = {}
            for param_name, param_info in self._params.items():
                model_params[param_name] = (param_info.annotation, param_info.default)
            self._model = create_model(model_name,
                                       __config__=get_config(dict(extra=extra)),
                                       **model_params)

    def _get_model_name(self) -> str:
        callable_name = _get_callable_name(self._callback)
        return f"model_{callable_name}_{self._input_device}"

    @staticmethod
    def _iter_over_async(async_generator: AsyncGenerator, loop: AbstractEventLoop):
        ait = async_generator.__aiter__()

        async def get_next():
            try:
                obj = await ait.__anext__()
                return False, obj
            except StopAsyncIteration:
                return True, None

        while True:
            done, obj = loop.run_until_complete(get_next())
            if done:
                break
            yield obj

    def __call__(self,
                 input_device: InputDevice,
                 message_bundle: MessageBundle) -> Optional[Union[PipelineResult, Iterable[PipelineResult]]]:
        kwargs: Dict[str, Any] = {}
        for param_name, param_info in self._special_params.items():
            if param_info.annotation is InputDeviceName:
                kwargs[param_name] = input_device.name
            elif param_info.annotation is MessageBundle:
                kwargs[param_name] = message_bundle
            elif param_info.annotation is Message:
                kwargs[param_name] = message_bundle.message

        if self._model:
            model = parse_raw_as(self._model, message_bundle.message.bytes)
            kwargs.update(dict(model))
        if self._is_async:
            callback_return = self._fastmessage_handler.event_loop.run_until_complete(self._callback(**kwargs))
        elif self._is_async_gen:
            callback_return = self._iter_over_async(self._callback(**kwargs), self._fastmessage_handler.event_loop)
        else:
            callback_return = self._callback(**kwargs)
        if callback_return is None:
            return None

        return self._get_pipeline_results(value=callback_return,
                                          default_output_device=self._output_device)

    def _get_pipeline_results(self,
                              value: Any,
                              default_output_device: Optional[str]) -> Iterable[PipelineResult]:

        if isinstance(value, (MultipleReturnValues, Generator)):
            return itertools.chain.from_iterable(map(lambda item: self._get_pipeline_results(item,
                                                                                             default_output_device),
                                                     value))

        elif isinstance(value, FastMessageOutput):
            return self._get_pipeline_results(value=value.value,
                                              default_output_device=value.output_device)
        else:
            pipeline_result = self._get_single_pipeline_result(value=value,
                                                               output_device=default_output_device)
            if pipeline_result is not None:
                return [pipeline_result]

        return []

    def _get_single_pipeline_result(self, value: Any, output_device: Optional[str]) -> Optional[PipelineResult]:
        if output_device is None:
            _logger.warning(f"callback for input device '{self._input_device}' returned value, "
                            f"but is not mapped to output device")
            return None

        if isinstance(value, MessageBundle):
            output_bundle = value
        elif isinstance(value, Message):
            output_bundle = MessageBundle(message=value)
        else:
            json_encoder = getattr(value, '__json_encoder__', BaseModel.__json_encoder__)
            output_data = json.dumps(value, default=json_encoder).encode()
            output_bundle = MessageBundle(message=Message(data=output_data))

        return PipelineResult(output_device_name=output_device, message_bundle=output_bundle)
