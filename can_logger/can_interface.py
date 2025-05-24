import asyncio
import can
from typing import Optional, Iterable

from can_logger.callbacks import AsyncCanMessageCallback


class CANInterface:
    def __init__(self, channel, fd_enabled: bool = True):
        self.channel: str = channel
        self.fd_enabled: bool = fd_enabled

        self.bus: Optional[can.interface.Bus] = None
        self.message_queue: Iterable[can.Message] = asyncio.Queue()
        self.running: bool = False

        self.receive_callbacks: list[AsyncCanMessageCallback] = []

    async def connect(self) -> None:
        try:
            self.bus = can.Bus(
                channel=self.channel,
                interface="socketcan",
                fd=self.fd_enabled,
            )

            self.running = True
            self.receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            raise

    async def send_frame(self, can_id, data, is_fd=True):
        pass

    async def receive_frame(self, timeout=None) -> can.Message | None:
        try:
            message: can.Message
            if timeout is not None:
                message = await asyncio.wait_for(self.message_queue.get(), timeout)
            else:
                message = await self.message_queue.get()

            self.message_queue.task_done()
            return message
        except asyncio.TimeoutError:
            return None

    async def _receive_loop(self) -> None:
        """Background task that continuously receives CAN frames."""
        loop = asyncio.get_running_loop()

        while self.running:
            try:
                message: can.Message = await loop.run_in_executor(
                    None, self.bus.recv, 0.1
                )
                if message is not None:
                    await self.message_queue.put(message)

                    for callback in self.receive_callbacks:
                        try:
                            asyncio.create_task(callback(message))
                        except Exception as e:
                            # await logger.error(f"Error in receive callback: {str(e)}")
                            pass

            except asyncio.CancelledError:
                break

            except Exception as e:
                # await logger.error(f"Error in receive loop: {str(e)}")
                await asyncio.sleep(0.1)

    def add_receive_callback(self, callback) -> None:
        """
        Add a callback to be called when a frame is received.

        Args:
            callback: Async function to call with CANMessage parameter
        """
        self.receive_callbacks.append(callback)

    def remove_receive_callback(self, callback) -> None:
        """Remove a receive callback."""
        if callback in self.receive_callbacks:
            self.receive_callbacks.remove(callback)

    async def disconnect(self):
        if not self.running:
            return

        self.running = False
        if self.receive_task is not None:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None

        # Close the bus
        if self.bus is not None:
            self.bus.shutdown()
            self.bus = None
