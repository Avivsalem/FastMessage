import threading
from typing import Optional

from messageflux import InputDevice, ReadResult


class FakeInputDevice(InputDevice):
    def _read_message(self,
                      cancellation_token: threading.Event,
                      timeout: Optional[float] = None,
                      with_transaction: bool = True) -> Optional['ReadResult']:
        return None

    def __init__(self, name: str):
        super().__init__(None, name)
