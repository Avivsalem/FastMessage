import json
import uuid
from typing import List

from fastmessage import FastMessage, InputDeviceName
from messageflux.iodevices.base.common import MessageBundle, Message
from tests.common import FakeInputDevice


def test_sanity_async():
    default_output_device = str(uuid.uuid4()).replace('-', '')
    fm: FastMessage = FastMessage(default_output_device=default_output_device)

    @fm.map()
    async def do_something1(x: int, y: str, z: List[int] = None):
        return dict(y=f'x={x}, y={y}, z={z}')

    result = fm.handle_message(FakeInputDevice('do_something1'),
                               MessageBundle(Message(b'{"x": 1, "y": "a", "F":3}')))
    assert result is not None
    result = result[0]
    assert result.output_device_name == default_output_device
    json_result = json.loads(result.message_bundle.message.bytes.decode())
    assert json_result['y'] == 'x=1, y=a, z=None'

    result = fm.handle_message(FakeInputDevice('do_something1'),
                               MessageBundle(Message(b'{"x": 1, "y": "a", "z":[1,2]}')))
    assert result is not None
    result = result[0]
    assert result.output_device_name == default_output_device
    json_result = json.loads(result.message_bundle.message.bytes.decode())
    assert json_result['y'] == 'x=1, y=a, z=[1, 2]'


def test_return_async_generator():
    default_output_device = str(uuid.uuid4()).replace('-', '')
    fm: FastMessage = FastMessage(default_output_device=default_output_device)

    @fm.map(input_device='input1')
    async def do_something1(m: Message, b: MessageBundle, d: InputDeviceName, y: int):
        yield 1
        yield 2
        yield 3

    result = fm.handle_message(FakeInputDevice('input1'),
                               MessageBundle(message=Message(data=b'{"y": 10}',
                                                             headers={'test': 'mtest'}),
                                             device_headers={'test': 'btest'}))
    assert result is not None
    result = list(result)
    assert len(result) == 3
    assert result[0].message_bundle.message.bytes == b'1'
    assert result[1].message_bundle.message.bytes == b'2'
    assert result[2].message_bundle.message.bytes == b'3'
