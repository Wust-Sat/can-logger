import can
import click
import signal
import sys
import sqlite3


class CanSniffer:
    """
    A class to sniff messages on a CAN bus using python-can.
    """

    def __init__(self, interface, bustype="socketcan", bitrate=None, db_path=None):
        """
        Initializes the CanSniffer.

        Args:
            interface (str): The CAN interface name (e.g., 'vcan0', 'can0').
            bustype (str): The python-can bus type (default: 'socketcan').
            bitrate (int, optional): The bitrate for physical interfaces.
                                     Defaults to None.
        """
        self.interface = interface
        self.bustype = bustype
        self.bitrate = bitrate
        self.db_path = db_path
        self.bus = None
        self._running = False

    def _format_message(self, msg: can.Message) -> str:
        """Formats a CAN message similar to candump output."""
        arbitration_id_str = f"{msg.arbitration_id:03X}"
        data_str = " ".join(f"{b:02X}" for b in msg.data)
        # Example: vcan0  123   [8]  DE AD BE EF 00 11 22 33
        return (
            f"  {self.interface:<5}  {arbitration_id_str:<3}   [{msg.dlc}]  {data_str}"
        )

    def connect(self):
        """Establishes connection to the CAN bus."""
        try:
            kwargs = {"channel": self.interface, "bustype": self.bustype, "fd": True}
            if self.bitrate:
                kwargs["bitrate"] = self.bitrate

            self.bus = can.interface.Bus(**kwargs)
            print(f"Successfully listening on {self.bus.channel_info}")
            self._running = True
        except OSError as e:
            print(
                f"Error: Cannot find or open CAN interface '{self.interface}'.",
                file=sys.stderr,
            )
            print(f"System error: {e}", file=sys.stderr)
            print(
                "Ensure the interface exists and is up (e.g., 'sudo ip link set vcan0"
                " up').",
                file=sys.stderr,
            )
            self._running = False
            raise  # Re-raise the exception to be caught by the caller
        except can.CanError as e:
            print(f"Error initializing CAN bus: {e}", file=sys.stderr)
            self._running = False
            raise  # Re-raise

    def sniff(self):
        """Starts sniffing messages and printing them."""
        if not self.bus or not self._running:
            print("Error: Bus is not connected.", file=sys.stderr)
            return

        print("Sniffing started. Press Ctrl+C to stop.")
        try:
            while self._running:
                msg = self.bus.recv(timeout=1)
                if msg.is_fd:
                    print("FD ", end="")
                elif not msg.is_fd:
                    print("ST ", end="")
                if msg is not None and self._running:
                    if msg.is_error_frame:
                        print(
                            f"ERROR FRAME: {msg.timestamp} {msg.data}",
                            file=sys.stderr,
                        )
                    else:
                        print(self._format_message(msg))
        except Exception as e:
            if self._running:
                print(f"\nAn error occurred during sniffing: {e}", file=sys.stderr)
        finally:
            pass

    def sniff_db(self):
        """Starts sniffing messages and saving them to an SQLite database."""

        if not self.bus or not self._running:
            print("Error: Bus is not connected.", file=sys.stderr)
            return

        print("Sniffing started. Press Ctrl+C to stop.")

        # Connect to SQLite database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute(
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
        conn.commit()

        try:
            while self._running:
                msg = self.bus.recv(timeout=1)
                if msg is not None and self._running:
                    # Save message to database
                    cursor.execute(
                        """
                        INSERT INTO can_messages (timestamp, arbitration_id, dlc, data, is_fd, is_error_frame)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            msg.timestamp,
                            f"{msg.arbitration_id:03X}",
                            msg.dlc,
                            " ".join(f"{b:02X}" for b in msg.data),
                            int(msg.is_fd),
                            int(msg.is_error_frame),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            if self._running:
                print(f"\nAn error occurred during sniffing: {e}", file=sys.stderr)
        finally:
            # Close the database connection
            conn.close()

    def shutdown(self):
        """Shuts down the CAN bus connection."""
        print("\nStopping sniffer...")
        self._running = False  # Signal the loop to stop
        if self.bus:
            try:
                self.bus.shutdown()
                print("CAN bus shut down.")
            except Exception as e:
                print(f"Error shutting down bus: {e}", file=sys.stderr)
        else:
            print("Bus was not initialized.")


# --- Click Command ---

# Global sniffer instance for the signal handler
sniffer_instance = None


def signal_handler(sig, frame):
    """Signal handler to stop the sniffer gracefully."""
    if sniffer_instance:
        sniffer_instance.shutdown()
    # sys.exit(0) # Shutdown might take a moment, exit after it finishes


@click.command()
@click.option(
    "-i",
    "--interface",
    required=True,
    type=str,
    help="CAN interface name (e.g., vcan0, can0).",
)
@click.option(
    "-b",
    "--bustype",
    default="socketcan",
    show_default=True,
    type=str,
    help="python-can bus type.",
)
@click.option(
    "--bitrate",
    type=int,
    default=None,
    help="Bitrate for physical interfaces (e.g., 500000).",
)
@click.option(
    "-d",
    "--db-path",
    type=str,
    default=None,
    help="Path to SQLite database file for saving messages.",
)
def main(interface, bustype, bitrate, db_path):
    """
    Simple CAN bus sniffer using python-can and click.
    Listens on the specified INTERFACE and prints received messages.
    """
    global sniffer_instance
    sniffer_instance = CanSniffer(interface, bustype, bitrate, db_path)

    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    try:
        sniffer_instance.connect()
        if sniffer_instance._running:
            sniffer_instance.sniff_db()  # This will run until stopped or error
    except (OSError, can.CanError):
        # Connection errors already printed by connect()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}", file=sys.stderr)
        if sniffer_instance:
            sniffer_instance.shutdown()  # Attempt cleanup
        sys.exit(1)
    finally:
        # Ensure shutdown is called even if sniff loop exits unexpectedly
        # (though signal handler is the primary mechanism for Ctrl+C)
        if sniffer_instance and sniffer_instance._running:
            sniffer_instance.shutdown()
        print("Exiting.")


if __name__ == "__main__":
    main()
