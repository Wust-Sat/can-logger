import asyncio

import click
from life_guard.life_center import Device, LifeGuard

from can_logger.can_interface import CANInterface
from can_logger.database import CANMessageDatabase


def setup_life_guard():
    lg = LifeGuard()
    lg.add_device(Device(node_id=1, name="Bat"))
    lg.add_device(Device(node_id=2, name="EPS1"))
    lg.add_device(Device(node_id=3, name="EPS2"))

    lg.init_from_config()
    lg = LifeGuard.init_from_config()

    return lg


async def async_main(interface, db_path):
    can_interface = CANInterface(interface)
    db_interface = CANMessageDatabase(db_path)

    lg = setup_life_guard()
    await lg.start()

    await can_interface.connect()
    db_interface.connect()

    async def monitorX(message):
        # print(lg.monitor(message))
        lg.monitor(message)

    def db_message_handler(message):
        db_interface.add_message(message)

    can_interface.add_receive_callback(db_message_handler)
    can_interface.add_receive_callback(monitorX)

    try:
        while can_interface.running:
            await can_interface.receive_frame(timeout=1.0)

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        await can_interface.disconnect()
        db_interface.disconnect()


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
