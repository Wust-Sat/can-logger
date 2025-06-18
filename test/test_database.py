import pytest
import pytest_asyncio
import can
from pathlib import Path
from can_logger.database import CANMessageDatabase


@pytest.fixture
def msg(mocker):
    msg = mocker.MagicMock(spec=can.Message)
    msg.timestamp = 123.456
    msg.arbitration_id = 0x1AB
    msg.dlc = 3
    msg.data = bytearray([0x01, 0x02, 0x03])
    msg.is_fd = True
    msg.is_error_frame = False
    return msg


@pytest_asyncio.fixture
async def db(mocker):
    
    mock_conn = mocker.patch(
        "can_logger.database.aiosqlite.connect", new_callable=mocker.AsyncMock
    )
    mock_cursor = mock_conn.return_value.cursor.return_value

    db = CANMessageDatabase("test.db")
    await db.connect()

    db._test_conn = mock_conn.return_value
    db._test_cursor = mock_cursor

    yield db

    if db.db_connected:
      await db.disconnect()


def test_database_init(db):
    assert db.db_path == Path("test.db")
    assert db.db_connected is True
    assert db.conn is db._test_conn
    assert db.cursor is db._test_cursor


@pytest.mark.asyncio
async def test_connect_creates_table_and_sets_connected(db):
    db._test_cursor.execute.assert_called_once()
    db._test_cursor.execute.assert_called_with(
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
    assert db.db_connected is True


@pytest.mark.asyncio
async def test_add_message_inserts_correct_data(db, msg):
    await db.add_message(msg)

    db._test_cursor.execute.assert_any_call(
        """
            INSERT INTO can_messages (timestamp, arbitration_id, dlc, data, is_fd, is_error_frame)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
        (
            msg.timestamp,
            f"{msg.arbitration_id:03X}",
            msg.dlc,
            "01 02 03",
            1,
            0,
        ),
    )
    db._test_conn.commit.assert_called()


@pytest.mark.asyncio
async def test_add_message_raises_if_not_connected(db, msg):
    db.db_connected = False

    with pytest.raises(RuntimeError, match="First connect to database."):
        await db.add_message(msg)


@pytest.mark.asyncio
async def test_disconnect_closes_cursor_and_connection(db):
    await db.disconnect()

    db._test_cursor.close.assert_called_once()
    db._test_conn.close.assert_called_once()
    assert db.db_connected is False

