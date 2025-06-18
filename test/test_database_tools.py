import pytest
from pathlib import Path
from datetime import datetime
from can_logger.database_tools.database_interface import DatabaseInterface


@pytest.fixture
def db(mocker):
    mock_conn = mocker.patch(
        "can_logger.database_tools.database_interface.sqlite3.connect", autospec=True
    )
    mock_cursor = mock_conn.return_value.cursor.return_value

    db = DatabaseInterface("test.db")
    db.connect()

    db._test_conn = mock_conn.return_value
    db._test_cursor = mock_cursor
    yield db

    if db.connected:
        db.disconnect()


def test_database_init(db):
    assert db.db_path == Path("test.db")
    assert db.connected is True
    assert db.conn is db._test_conn
    assert db.cursor is db._test_cursor


def test_disconnect_closes_cursor_and_connection(db):
    db.disconnect()

    db._test_cursor.close.assert_called_once()
    db._test_conn.close.assert_called_once()
    assert db.connected is False


def test_check_connection_raises_without_connect():
    db = DatabaseInterface("no_connect.db")

    with pytest.raises(RuntimeError, match="First connect to database!"):
        db.get_all_messages()


def test_get_all_messages_executes_query(db):
    db.get_all_messages()

    db._test_cursor.execute.assert_called_once_with("SELECT * FROM can_messages", ())
    db._test_cursor.fetchall.assert_called_once()


def test_get_last_n_messages_executes_query(db):
    db.get_last_n_messages(5)

    db._test_cursor.execute.assert_called_once_with(
        "SELECT * FROM can_messages ORDER BY id DESC LIMIT ?", (5,)
    )
    db._test_cursor.fetchall.assert_called_once()


def test_get_messages_by_arbitration_id_executes_query(db):
    db.get_messages_by_arbitration_id("1AB")

    db._test_cursor.execute.assert_called_once_with(
        "SELECT * FROM can_messages WHERE arbitration_id = ?", ("1AB",)
    )
    db._test_cursor.fetchall.assert_called_once()


@pytest.mark.parametrize(
    "args, start_str, end_str",
    [
        (
            ("2025-01-01", None, None),
            "2025-01-01 00:00:00",
            "2025-01-01 23:59:59.999999",
        ),
        (("2025-01-02", 14, None), "2025-01-02 14:00:00", "2025-01-02 14:59:59.999999"),
        (("2025-01-03", 9, 15), "2025-01-03 09:15:00", "2025-01-03 09:15:59.999999"),
    ],
)
def test_get_messages_by_datetime_builds_correct_range(db, args, start_str, end_str):
    start_ts = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S").timestamp()
    end_ts = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S.%f").timestamp()

    db.get_messages_by_datetime(*args)

    db._test_cursor.execute.assert_called_once_with(
        "SELECT * FROM can_messages WHERE timestamp >= ? AND timestamp <= ?",
        (start_ts, end_ts),
    )
    db._test_cursor.fetchall.assert_called_once()
