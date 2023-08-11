import pytest

from fastmessage import FastMessage, MissingCallbackException
from fastmessage.exceptions import MethodValidationError
from fastmessage.method_validator import MethodValidator
from messageflux.iodevices.base.common import MessageBundle, Message
from tests.common import FakeInputDevice


def test_by_method():
    fm: FastMessage = FastMessage()

    @fm.map()
    def func_input(method_validator: MethodValidator):
        return method_validator.validate_and_return(func_output, x=3, y="hello")

    @fm.map(input_device='func2_device', output_device='output')
    def func_output(x: int, y: str):
        return f"Success: x={x}, y={y}"

    result = fm.handle_message(FakeInputDevice('func_input'), MessageBundle(message=Message(data=b'{"y": 10}')))
    assert result is not None
    result = list(result)
    assert len(result) == 1
    assert result[0].output_device_name == "func2_device"

    result = fm.handle_message(FakeInputDevice(result[0].output_device_name), result[0].message_bundle)
    assert result is not None
    result = list(result)
    assert len(result) == 1
    assert result[0].message_bundle.message.bytes == b'"Success: x=3, y=hello"'


def test_by_input_device_name():
    fm: FastMessage = FastMessage()

    @fm.map()
    def func_input(method_validator: MethodValidator):
        return method_validator.validate_and_return("func2_device", x=3, y="hello")

    @fm.map(input_device='func2_device', output_device='output')
    def func_output(x: int, y: str):
        return f"Success: x={x}, y={y}"

    result = fm.handle_message(FakeInputDevice('func_input'), MessageBundle(message=Message(data=b'{"y": 10}')))
    assert result is not None
    result = list(result)
    assert len(result) == 1
    assert result[0].output_device_name == "func2_device"

    result = fm.handle_message(FakeInputDevice(result[0].output_device_name), result[0].message_bundle)
    assert result is not None
    result = list(result)
    assert len(result) == 1
    assert result[0].message_bundle.message.bytes == b'"Success: x=3, y=hello"'


def test_validation_error():
    fm: FastMessage = FastMessage()

    @fm.map()
    def func_input(method_validator: MethodValidator):
        return method_validator.validate_and_return("func2_device", x=3)

    @fm.map(input_device='func2_device', output_device='output')
    def func_output(x: int, y: str):
        return f"Success: x={x}, y={y}"

    with pytest.raises(MethodValidationError):
        _ = fm.handle_message(FakeInputDevice('func_input'), MessageBundle(message=Message(data=b'{"y": 10}')))


def test_missing_callback():
    fm: FastMessage = FastMessage()

    @fm.map()
    def func_input(method_validator: MethodValidator):
        return method_validator.validate_and_return(func_output, x=3)

    def func_output(x: int, y: str):
        return f"Success: x={x}, y={y}"

    with pytest.raises(MissingCallbackException):
        _ = fm.handle_message(FakeInputDevice('func_input'), MessageBundle(message=Message(data=b'{"y": 10}')))
