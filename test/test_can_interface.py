import pytest
import pytest_asyncio
import can
import asyncio
from can_logger.can_interface import CANInterface


@pytest_asyncio.fixture
async def can_interface(mocker):
    mock_can_bus = mocker.patch(
        "can_logger.can_interface.can.Bus")
    mock_bus = mock_can_bus.return_value
    mock_bus.recv.return_value = None
    
    can_interface = CANInterface(channel="vcan0", fd_enabled=False)

    await can_interface.connect()

    can_interface._test_can_bus = mock_can_bus
    can_interface._test_bus = mock_bus

    yield can_interface

    if can_interface.running:
        await can_interface.disconnect()


def test_can_interface_init(can_interface):
    assert can_interface.channel == "vcan0"
    assert can_interface.fd_enabled is False


@pytest.mark.asyncio
async def test_connect_sets_bus_and_running(can_interface):
    assert can_interface.bus is can_interface._test_bus
    assert can_interface.running is True
    assert can_interface.receive_task is not None
    assert isinstance(can_interface.receive_task, asyncio.Task)
    can_interface._test_can_bus.assert_called_once_with(
        channel="vcan0",
        interface="socketcan",
        fd=False,
    )


@pytest.mark.asyncio
async def test_connect_sets_bus_connected_false_on_exception(mocker, can_interface):
    mocker.patch(
        "can_logger.can_interface.can.Bus", side_effect=RuntimeError("Bus error")
    )

    await can_interface.connect()

    assert can_interface.running is False


@pytest.mark.asyncio
async def test_disconnect_stops_running(can_interface):
    await can_interface.disconnect()

    assert can_interface.running is False
    assert can_interface.bus is None



@pytest.mark.asyncio
async def test_receive_frame_returns_message(mocker, can_interface):
    mock_msg = mocker.Mock(spec=can.Message)

    await can_interface.message_queue.put(mock_msg)
    result = await can_interface.receive_frame(timeout=0.1)

    assert result is mock_msg


@pytest.mark.asyncio
async def test_receive_frame_timeout(can_interface):
    result = await can_interface.receive_frame(timeout=0.01)
    assert result is None


def test_add_and_remove_receive_callback(mocker, can_interface):
    mock_cb = mocker.MagicMock()

    can_interface.add_receive_callback(mock_cb)
    assert mock_cb in can_interface.receive_callbacks

    can_interface.remove_receive_callback(mock_cb)
    assert mock_cb not in can_interface.receive_callbacks


@pytest.mark.asyncio
async def test_connect_and_receive_message(mocker):
    mock_msg = mocker.Mock(spec=can.Message)
    mock_can_bus = mocker.patch("can_logger.can_interface.can.Bus")
    mock_bus = mock_can_bus.return_value
    mock_bus.recv = mocker.MagicMock(side_effect=[mock_msg])

    iface = CANInterface("vcan0", fd_enabled=False)
    await iface.connect()

    result = await iface.receive_frame(timeout=0.1)

    assert result is mock_msg
    mock_bus.recv.assert_called()
    assert iface.bus is mock_bus

    await iface.disconnect()
