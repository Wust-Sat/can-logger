import asyncio
import click

from can_logger.callbacks import format_message
from can_logger.can_interface import CANInterface
from can_logger.database import CANMessageDatabase


async def async_main(interface, db_path):
    can_interface = CANInterface(interface)
    db_interface = CANMessageDatabase(db_path)

    await can_interface.connect()
    await db_interface.connect()

    async def message_printer(message):
        print(format_message(message))

    async def db_message_handler(message):
        await db_interface.add_message(message)

    can_interface.add_receive_callback(message_printer)
    can_interface.add_receive_callback(db_message_handler)

    try:
        while can_interface.running:
            await can_interface.receive_frame(timeout=1.0)

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        await can_interface.disconnect()
        await db_interface.disconnect()


@click.command()
@click.option(
    "-i",
    "--interface",
    required=True,
    type=str,
    help="CAN interface name (e.g., vcan0, can0).",
)
@click.option(
    "-d",
    "--db-path",
    type=str,
    default="can_messages.db",
    help="Path to SQLite database file for saving messages.",
)
def main(interface, db_path):
    asyncio.run(async_main(interface, db_path))


if __name__ == "__main__":
    main()
