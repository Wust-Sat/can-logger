import click
import re
from database_tools.database_interface import DatabaseInterface


def print_messages(messages: list) -> None:
    if messages:
        for mes in messages:
            print(mes)


@click.command()
@click.option(
    "-d",
    "--db-path",
    type=str,
    default="../can_messages.db",
    help="Path to SQLite database file for saving messages.",
)
@click.option(
    "--mode",
    type=click.Choice(["all", "last", "id", "date"], case_sensitive=False),
    default="all",
    help="Choose operation mode.",
)
@click.option(
    "-n",
    type=int,
    default=10,
    help="Number of last messages (for 'last' mode).",
)
@click.option(
    "-id",
    "--arbitration-id",
    type=str,
    default=None,
    help="Arbitration ID (for 'id' mode).",
)
@click.option(
    "-d",
    "--date",
    type=str,
    default=None,
    help="Date in format YYYY-MM-DD (year-month-day) (for 'date' mode).",
)
@click.option(
    "-h",
    "--hour",
    type=int,
    default=None,
    help="Hour (for 'date' mode).",
)
@click.option(
    "-m",
    "--minute",
    type=int,
    default=None,
    help="Minute (for 'date' mode).",
)
def main(db_path, mode, n, arbitration_id, date, hour, minute):
    db_interface = DatabaseInterface(db_path)
    db_interface.connect()

    if mode == "all":
        print_messages(db_interface.get_all_messages())
    elif mode == "last":
        print_messages(db_interface.get_last_n_messages(n))
    elif mode == "id":
        print_messages(db_interface.get_messages_by_arbitration_id(arbitration_id))
    elif mode == "date":
        if not date:
            print("You must provide a date for 'date' mode.")
        else:
            # Check if date matches YYYY-MM-DD
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                print("Date must be in format YYYY-MM-DD (year-month-day).")
            else:
                print_messages(db_interface.get_messages_by_datetime(date, hour, minute))

    db_interface.disconnect()


if __name__ == "__main__":
    main()
