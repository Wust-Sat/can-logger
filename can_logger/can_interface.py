import asyncio
import can
from typing import Optional
import sqlite3
import click

from can_logger.callbacks import AsyncCanMessageCallback, format_message


class CANInterface:
    def __init__(self, channel, fd_enabled, db_path):
        self.channel: str = channel
        self.fd_enabled: bool = fd_enabled
        self.db_path: str = db_path

        self.bus: Optional[can.interface.Bus] = None
        self.message_queue = asyncio.Queue()
        self.running: bool = False

        self.db_connected: bool = False

        self.receive_callbacks: list[AsyncCanMessageCallback] = []

    async def connect(self) -> None:
        try:
            self.bus = can.Bus(
                channel=self.channel,
                interface="socketcan",
                fd_en=self.fd_enabled,
            )

            self.connect_db()

            self.running = True
            self.receive_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            raise

    def connect_db(self) -> None:
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS can_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    arbitration_id TEXT,
                    dlc INTEGER,
                    data TEXT,
                    is_fd INTEGER,
                    is_error_frame INTEGER
                )
                """
            )
            self.conn.commit()
            self.db_connected = True
        except Exception as e:
            self.db_connected = False

    def add_message_to_db(self, message: can.Message) -> None:
        # Save message to database
        self.cursor.execute(
            """
            INSERT INTO can_messages (timestamp, arbitration_id, dlc, data, is_fd, is_error_frame)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message.timestamp,
                f"{message.arbitration_id:03X}",
                message.dlc,
                " ".join(f"{b:02X}" for b in message.data),
                int(message.is_fd),
                int(message.is_error_frame),
            ),
        )
        self.conn.commit()

    async def send_frame(self, can_id, data, is_fd=True):
        pass

    async def receive_frame(self, timeout=None):
        try:
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
                message = await loop.run_in_executor(None, self.bus.recv, 0.1)
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

        # Close the database connection
        if self.db_connected:
            self.cursor.close()
            self.conn.close()
            self.db_connected = False

@click.command()
@click.option(
    "-i",
    "--interface",
    required=True,
    type=str,
    help="CAN interface name (e.g., vcan0, can0).",
)
@click.option(
    "--fd-enable/--no-fd-enable",
    default=True,
    help="Enable or disable CAN FD support.",
)
@click.option(
    "-d",
    "--db-path",
    type=str,
    default="can_messages.db",
    help="Path to SQLite database file for saving messages.",
)
def main(interface, fd_enable, db_path):
    asyncio.run(async_main(interface, fd_enable, db_path))

async def async_main(interface, fd_enable, db_path):
    can_interface = CANInterface(interface, fd_enable, db_path)
    await can_interface.connect()

    async def message_handler(message):
        print(format_message(message))

    async def db_message_handler(message):
        can_interface.add_message_to_db(message)

    can_interface.add_receive_callback(message_handler)
    can_interface.add_receive_callback(db_message_handler)

    try:
        while can_interface.running:
            await can_interface.receive_frame(timeout=1.0)

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        await can_interface.disconnect()


if __name__ == "__main__":
    main()
