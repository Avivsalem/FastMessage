import inspect
import json
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any, Union, Iterable, Generator, AsyncGenerator, TYPE_CHECKING, Callable, Type

import itertools
from pydantic import BaseModel, create_model, Extra
from pydantic.config import get_config
from pydantic.typing import get_all_type_hints

from fastmessage.common import CustomOutput, InputDeviceName, MultipleReturnValues, OtherMethodOutput
from fastmessage.common import _CALLABLE_TYPE, get_callable_name, _logger
from fastmessage.exceptions import NotAllowedParamKindException, SpecialDefaultValueException
from fastmessage.method_validator import MethodValidator
from messageflux import InputDevice
from messageflux.iodevices.base.common import MessageBundle, Message
from messageflux.pipeline_service import PipelineResult

if TYPE_CHECKING:
    from fastmessage.fastmessage_handler import FastMessage


class _CallableType(Enum):
    SYNC = auto()
    ASYNC = auto()
    ASYNC_GENERATOR = auto()


@dataclass
class _ParamInfo:
    annotation: Any
    default: Any


@dataclass
class _CallableAnalysis:
    params: Dict[str, _ParamInfo]
    special_params: Dict[str, _ParamInfo]
    has_kwargs: bool
    callable_type: _CallableType


class CallableWrapper:
    """
    a helper class that wraps a callable
    """

    def __init__(self, *,
                 fastmessage_handler: 'FastMessage',
                 wrapped_callable: _CALLABLE_TYPE,
                 input_device_name: str,
                 output_device_name: Optional[str] = None):
        self._fastmessage_handler = fastmessage_handler
        self._callable = wrapped_callable
        self._input_device_name = input_device_name
        self._output_device_name = output_device_name
        self._method_validator = MethodValidator(self._fastmessage_handler)

        self._callable_analysis = self._analyze_callable(self._callable)
        self._model: Type[BaseModel] = self._create_model(model_name=self._get_model_name(),
                                                          callable_analysis=self._callable_analysis)

    @staticmethod
    def _analyze_callable(wrapped_callable: _CALLABLE_TYPE) -> _CallableAnalysis:
        params = dict()
        special_params = dict()
        type_hints = get_all_type_hints(wrapped_callable)
        has_kwargs = False
        for param_name, param in inspect.signature(wrapped_callable).parameters.items():
            if param.kind in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL):
                raise NotAllowedParamKindException(
                    f"param '{param_name}' is of '{param.kind}' kind. this is now allowed")

            if param.kind == param.VAR_KEYWORD:  # there's **kwargs param
                has_kwargs = True
                continue

            annotation = Any if param.annotation is param.empty else type_hints[param_name]
            default = ... if param.default is param.empty else param.default

            param_info = _ParamInfo(annotation=annotation, default=default)

            if param_info.annotation in (MessageBundle, Optional[MessageBundle],
                                         Message, Optional[Message],
                                         InputDeviceName, Optional[InputDeviceName],
                                         MethodValidator, Optional[MethodValidator]):
                if param_info.default is not ...:
                    raise SpecialDefaultValueException(
                        f"param '{param_name}' is of special type '{param.annotation.__name__}' "
                        f"but has a default value")
                special_params[param_name] = param_info

            else:
                params[param_name] = param_info

        callable_type = _CallableType.SYNC
        if inspect.iscoroutinefunction(wrapped_callable):
            callable_type = _CallableType.ASYNC
        elif inspect.isasyncgenfunction(wrapped_callable):
            callable_type = _CallableType.ASYNC_GENERATOR

        return _CallableAnalysis(params=params,
                                 special_params=special_params,
                                 has_kwargs=has_kwargs,
                                 callable_type=callable_type)

    @staticmethod
    def _create_model(model_name: str, callable_analysis: _CallableAnalysis) -> Type[BaseModel]:
        model_params: Dict[str, Any] = {}
        for param_name, param_info in callable_analysis.params.items():
            model_params[param_name] = (param_info.annotation, param_info.default)
        extra = Extra.allow if callable_analysis.has_kwargs else Extra.ignore
        model = create_model(model_name,
                             __config__=get_config(dict(extra=extra)),
                             **model_params)

        return model

    @property
    def model(self) -> Type[BaseModel]:
        """
        the model that was created for this callable (if it has input params)
        """
        return self._model

    @property
    def callable(self) -> Callable:
        """
        the original callable that was passed to this wrapper
        """
        return self._callable

    @property
    def input_device_name(self) -> str:
        """
        the input device name for this callable
        """
        return self._input_device_name

    @property
    def output_device_name(self) -> Optional[str]:
        """
        the default output device name for this callable
        """
        return self._output_device_name

    def _get_model_name(self) -> str:
        callable_name = get_callable_name(self._callable)
        return f"model_{callable_name}_{self._input_device_name}"

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
        for param_name, param_info in self._callable_analysis.special_params.items():
            if param_info.annotation is InputDeviceName:
                kwargs[param_name] = input_device.name
            elif param_info.annotation is MessageBundle:
                kwargs[param_name] = message_bundle
            elif param_info.annotation is Message:
                kwargs[param_name] = message_bundle.message
            elif param_info.annotation is MethodValidator:
                kwargs[param_name] = self._method_validator

        model: BaseModel = self._model.parse_raw(message_bundle.message.bytes)
        kwargs.update(dict(model))

        if self._callable_analysis.callable_type == _CallableType.ASYNC:
            callback_return = self._fastmessage_handler.event_loop.run_until_complete(self._callable(**kwargs))

        elif self._callable_analysis.callable_type == _CallableType.ASYNC_GENERATOR:
            callback_return = self._iter_over_async(self._callable(**kwargs), self._fastmessage_handler.event_loop)

        else:
            callback_return = self._callable(**kwargs)

        if callback_return is None:
            return None

        return self._get_pipeline_results(value=callback_return,
                                          default_output_device=self._output_device_name)

    def _get_pipeline_results(self,
                              value: Any,
                              default_output_device: Optional[str]) -> Iterable[PipelineResult]:

        if isinstance(value, (MultipleReturnValues, Generator)):
            return itertools.chain.from_iterable(map(lambda item: self._get_pipeline_results(item,
                                                                                             default_output_device),
                                                     value))

        elif isinstance(value, CustomOutput):
            return self._get_pipeline_results(value=value.value,
                                              default_output_device=value.output_device)
        elif isinstance(value, OtherMethodOutput):
            custom_output = self._method_validator.validate_and_return(value.method, **value.kwargs)

            return self._get_pipeline_results(value=custom_output.value,
                                              default_output_device=custom_output.output_device)
        else:
            pipeline_result = self._get_single_pipeline_result(value=value,
                                                               output_device=default_output_device)
            if pipeline_result is not None:
                return [pipeline_result]

        return []

    def _get_single_pipeline_result(self, value: Any, output_device: Optional[str]) -> Optional[PipelineResult]:
        if output_device is None:
            _logger.warning(f"callback for input device '{self._input_device_name}' returned value, "
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
