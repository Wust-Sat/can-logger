import can
import aiosqlite
from aiosqlite import Connection, Cursor
from pathlib import Path


class CANMessageDatabase:
    def __init__(self, db_path: str | Path):
        self.db_path: Path = Path(db_path)
        self.db_connected: bool | None = None
        self.conn: Connection = None
        self.cursor: Cursor = None

    async def connect(self) -> None:
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.cursor = await self.conn.cursor()
            await self.cursor.execute(
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
            await self.conn.commit()
            self.db_connected = True
        except Exception as e:
            self.db_connected = False

    async def add_message(self, message: can.Message) -> None:
        if not self.db_connected:
            raise RuntimeError("First connect to database.")

        # Save message to database
        await self.cursor.execute(
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
        await self.conn.commit()

    async def disconnect(self) -> None:
        if self.db_connected:
            await self.cursor.close()
            await self.conn.close()
            self.db_connected = False
