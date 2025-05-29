import asyncio
import time
from enum import IntEnum
from threading import Event
from typing import Awaitable, Callable

import can
from pydantic import BaseModel

AsyncCanMessageCallback = Callable[[can.Message], Awaitable[None]]


class Status(IntEnum):
    BOOT_UP = 0x00
    STOPPED = 0x04
    OPERATIONAL = 0x05
    PRE_OPERATIONAL = 0x7F
    UNKNOWN = -0x01


class Device(BaseModel):
    node_id: int
    name: str
    status: Status = Status.BOOT_UP
    bootCounter: int = 0
    lastStamp: float = 0


class LifeGuard:
    @classmethod
    def init_from_config(cls, config: dict) -> "LifeGuard":
        pass

    def __init__(self):
        self.devices: list[Device] = []
        self._running = False
        self.bus = can.interface.Bus(channel="vcan0", bustype="socketcan", fd=True)

    def add_device(self, dev: Device) -> None:
        """Adds a device to the devices list."""
        self.devices.append(dev)

    def remove_device(self, dev: Device) -> None:
        """Remove a device from the devices list."""
        self.devices.remove(dev)

    def monitor(self, msg: can.Message) -> str:

        if not (0x10700 <= msg.arbitration_id <= 0x1077F):
            arg = "Its nothing"
        else:
            arg = "I feel HearthBeat!"

            id = msg.arbitration_id - 0x10700

            dev = next((dev for dev in self.devices if dev.node_id == id), None)

            if dev:
                dev.status = Status(msg.data[0])
                dev.lastStamp = msg.timestamp
            else:
                print("This device doesn't exist!")

        return f"{arg}"

    async def watchman(self):
        while 1:
            for dev in self.devices:
                if dev.status != Status.UNKNOWN:
                    if time.time() - dev.lastStamp > 3:
                        dev.status = Status.UNKNOWN
            await asyncio.sleep(1)

    async def start(self):
        """Start the background tasks"""
        self._running = True
        # Create task but don't await it yet
        self._watch_task = asyncio.create_task(self.watchman())
        self._print_task = asyncio.create_task(self.printStatusList())

    async def stop(self):
        """Clean shutdown"""
        self._running = False
        await self._watch_task  # Wait for task to complete
        print("LifeGuard stopped")

    async def printStatusList(self) -> None:
        while 1:
            print("------------------")
            print("NAME:\tSTATUS")
            for dev in self.devices:
                print(f"{dev.name}:\t{dev.status.name}")
            print("------------------")
            await asyncio.sleep(1)

    def send_state_change(self, node_id: int, target_state: str):
        state_commands = {
            "operational": 0x01,
            "stopped": 0x02,
            "pre-operational": 0x80,
            "reset": 0x81,
        }

        msg = can.Message(
            arbitration_id=0x10000000,
            data=[state_commands[target_state], node_id],
            is_fd=True,
            dlc=2,
        )
        self.bus.send(msg)


class Dummy:
    def __init__(self, node_id, channel="vcan0"):
        self._running = Event()
        self.bus = can.interface.Bus(channel=channel, bustype="socketcan", fd=True)
        self.node_id = node_id
        self.status = Status.BOOT_UP
        self.lastChange = time.time()

    async def start(self):
        """Start sender and receiver threads concurrently"""
        self._running.set()
        try:
            asyncio.create_task(self._statusMonitor())
            asyncio.create_task(self._sender())
            asyncio.create_task(self._receiver())

            while True:
                await asyncio.sleep(10)

        finally:
            self.bus.shutdown()

    async def _sender(self):
        """Thread: Continuously send messages"""
        while self._running.is_set():
            msg = can.Message(
                arbitration_id=0x10700 + self.node_id, data=[self.status], is_fd=True
            )
            self.bus.send(msg)

            await asyncio.sleep(1)

    async def _receiver(self):
        """Async CAN frame receiver"""
        while self._running:
            try:
                msg = await asyncio.to_thread(self.bus.recv, timeout=0.1)
                if msg:
                    await self._process_frame(msg)
            except (can.CanError, RuntimeError) as e:
                print(f"Receiver error: {e}")
                await self.stop()
                break

    async def _process_frame(self, msg):
        if msg.arbitration_id == 0x10000000 and msg.data[1] == self.node_id:
            if msg.data[0] == 0x81:  # reset
                self.status = Status.BOOT_UP
                self.lastChange = time.time()

            elif msg.data[0] == 0x01:  # start
                if self.status == Status.PRE_OPERATIONAL:
                    self.status = Status.OPERATIONAL
                    self.lastChange = time.time()
            elif msg.data[0] == 0x02:  # stop
                if (
                    self.status == Status.PRE_OPERATIONAL
                    or self.status == Status.OPERATIONAL
                ):
                    self.status = Status.STOPPED
                    self.lastChange = time.time()
            elif msg.data[0] == 0x80:  # pre-op
                if self.status == Status.STOPPED or self.status == Status.OPERATIONAL:
                    self.status = Status.PRE_OPERATIONAL
                    self.lastChange = time.time()

    async def _statusMonitor(self):
        """Thread: Continuously monitor and change in need status"""
        while self._running.is_set():
            if self.status == Status.BOOT_UP:
                if time.time() - self.lastChange > 3:
                    self.status = Status.PRE_OPERATIONAL
            await asyncio.sleep(1)

    async def stop(self):
        """Graceful shutdown"""
        self._running.clear()
        print(f"stopped {self.node_id}")
        await asyncio.sleep(1)
