import asyncio

import click

from can_logger.callbacks import format_message
from can_logger.can_interface import CANInterface
from can_logger.database import CANMessageDatabase
from components_life_guard.life_center import Device, LifeGuard
from components_life_guard.config import config


def setup_life_guard() -> LifeGuard:
    lg = LifeGuard()
    for key, value in config.items():
        lg.add_device(Device(node_id=value["node_id"], name=key))
    return lg


async def async_main(interface, db_path):
    can_interface = CANInterface(interface)
    db_interface = CANMessageDatabase(db_path)
    life_guard: LifeGuard = setup_life_guard()

    await can_interface.connect()
    await db_interface.connect()
    await life_guard.start()

    async def life_guard_handler(message):
        nonlocal life_guard
        # print(life_guard.monitor(message))
        life_guard.monitor(message)

    async def message_printer(message):
        print(format_message(message))

    async def db_message_handler(message):
        await db_interface.add_message(message)

    can_interface.add_receive_callback(message_printer)
    can_interface.add_receive_callback(db_message_handler)
    can_interface.add_receive_callback(life_guard_handler)

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
