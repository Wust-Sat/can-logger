import sqlite3
from sqlite3 import Connection, Cursor
from pathlib import Path
from datetime import datetime


class DatabaseInterface:
    def __init__(self, db_path: str | Path):
        self.db_path: Path = Path(db_path)
        self.tab_name: str = "can_messages"
        self.conn: Connection = None
        self.cursor: Cursor = None
        self.connected: bool = False

    def _check_connection(self):
        if not self.connected:
            raise RuntimeError("First connect to database!")

    def _execute_query(self, query: str, params: tuple = ()) -> list | None:
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()

        except Exception as e:
            print(f"Database error: {e}")
            return None

    def connect(self) -> None:
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.connected = True
        except Exception as e:
            self.connected = False
            print(f"Database connect error: {e}")

    def disconnect(self) -> None:
        if self.connected:
            self.cursor.close()
            self.conn.close()
            self.connected = False

    def get_all_messages(self) -> list | None:
        self._check_connection()
        return self._execute_query(f"SELECT * FROM {self.tab_name}")

    def get_last_n_messages(self, n: int) -> list | None:
        self._check_connection()
        return self._execute_query(
            f"SELECT * FROM {self.tab_name} ORDER BY id DESC LIMIT ?", (n,)
        )

    def get_messages_by_arbitration_id(self, arbitration_id: str) -> list | None:
        self._check_connection()
        return self._execute_query(
            f"SELECT * FROM {self.tab_name} WHERE arbitration_id = ?", (arbitration_id,)
        )

    def get_messages_by_datetime(
        self, date: str, hour: int = None, minute: int = None
    ) -> list | None:
        self._check_connection()

        if hour is not None and minute is not None:
            dt_start = datetime.strptime(
                f"{date} {hour:02d}:{minute:02d}:00", "%Y-%m-%d %H:%M:%S"
            )
            dt_end = datetime.strptime(
                f"{date} {hour:02d}:{minute:02d}:59.999999", "%Y-%m-%d %H:%M:%S.%f"
            )
        elif hour is not None:
            dt_start = datetime.strptime(
                f"{date} {hour:02d}:00:00", "%Y-%m-%d %H:%M:%S"
            )
            dt_end = datetime.strptime(
                f"{date} {hour:02d}:59:59.999999", "%Y-%m-%d %H:%M:%S.%f"
            )
        else:
            dt_start = datetime.strptime(f"{date} 00:00:00", "%Y-%m-%d %H:%M:%S")
            dt_end = datetime.strptime(
                f"{date} 23:59:59.999999", "%Y-%m-%d %H:%M:%S.%f"
            )

        ts_start = dt_start.timestamp()
        ts_end = dt_end.timestamp()

        return self._execute_query(
            f"SELECT * FROM {self.tab_name} WHERE timestamp >= ? AND timestamp <= ?",
            (ts_start, ts_end),
        )
