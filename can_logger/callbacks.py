import can
from typing import Callable, Awaitable

AsyncCanMessageCallback = Callable[[can.Message], Awaitable[None]]


def format_message(msg: can.Message) -> str:
    """Formats a CAN message similar to candump output."""
    channel: str = "vcan0"
    arbitration_id_str = f"{msg.arbitration_id:03X}"
    data_str = " ".join(f"{b:02X}" for b in msg.data)
    return f"  {channel:<5}  {arbitration_id_str:<3}   [{msg.dlc}]  {data_str}"
