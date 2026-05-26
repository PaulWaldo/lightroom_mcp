"""
Unit tests for mcp_server.shared.resilient_client.ResilientClientManager

Verifies retry logic, connection error detection, and reconnection behaviour
without any real socket connections.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.shared.resilient_client import ResilientClientManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONNECTION_ERROR_STRINGS = [
    "connection reset by peer",
    "broken pipe",
    "connection lost",
    "connection closed unexpectedly",
    "errno 54",
    "errno 32",
    "not connected",
]

NON_CONNECTION_ERRORS = [
    "invalid parameter value",
    "photo not found",
    "lua handler error",
]


def _manager_with_client(mock_client: MagicMock) -> ResilientClientManager:
    """Return a ResilientClientManager whose _client is pre-set to mock_client."""
    manager = ResilientClientManager()
    manager._client = mock_client
    return manager


def _make_client(return_value=None, side_effect=None) -> MagicMock:
    client = MagicMock()
    client.execute_command = AsyncMock(
        return_value=return_value or {"ok": True},
        side_effect=side_effect,
    )
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# execute_with_retry — happy path
# ---------------------------------------------------------------------------

async def test_execute_returns_result_on_first_attempt():
    client = _make_client(return_value={"ok": True})
    manager = _manager_with_client(client)

    result = await manager.execute_with_retry("system.ping")

    assert result == {"ok": True}
    client.execute_command.assert_awaited_once_with("system.ping", None)


async def test_execute_passes_params_through():
    client = _make_client(return_value={"photoId": "p-1"})
    manager = _manager_with_client(client)

    await manager.execute_with_retry("develop.setValue", {"param": "Exposure", "value": 0.5})

    client.execute_command.assert_awaited_once_with(
        "develop.setValue", {"param": "Exposure", "value": 0.5}
    )


# ---------------------------------------------------------------------------
# execute_with_retry — non-connection errors propagate immediately (no retry)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", NON_CONNECTION_ERRORS)
async def test_non_connection_error_raised_immediately(msg):
    client = _make_client(side_effect=ValueError(msg))
    manager = _manager_with_client(client)

    with pytest.raises(ValueError, match=msg):
        await manager.execute_with_retry("some.command", max_retries=3)

    # Should NOT have retried — only one call
    assert client.execute_command.await_count == 1


# ---------------------------------------------------------------------------
# execute_with_retry — connection errors trigger reconnect & retry
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("err_msg", CONNECTION_ERROR_STRINGS)
async def test_connection_error_triggers_retry_and_succeeds(err_msg):
    """A recognised connection error string causes a reconnect and retry."""
    bad_client = _make_client(side_effect=Exception(err_msg))
    good_client = _make_client(return_value={"recovered": True})

    manager = ResilientClientManager()
    manager._client = bad_client

    with patch(
        "mcp_server.shared.resilient_client.LightroomClient",
        return_value=good_client,
    ):
        result = await manager.execute_with_retry("cmd", max_retries=2)

    assert result == {"recovered": True}


async def test_all_retries_exhausted_raises_last_error():
    """When every attempt fails with a connection error the last one is re-raised."""
    bad_client = _make_client(side_effect=Exception("connection reset by peer"))

    manager = ResilientClientManager()
    manager._client = bad_client

    with patch(
        "mcp_server.shared.resilient_client.LightroomClient",
        return_value=bad_client,
    ):
        with pytest.raises(Exception, match="connection reset"):
            await manager.execute_with_retry("cmd", max_retries=2)


# ---------------------------------------------------------------------------
# connect / disconnect lifecycle
# ---------------------------------------------------------------------------

async def test_connect_creates_client_and_connects():
    mock_client = _make_client()

    with patch(
        "mcp_server.shared.resilient_client.LightroomClient",
        return_value=mock_client,
    ):
        manager = ResilientClientManager()
        await manager.connect()

    mock_client.connect.assert_awaited_once()
    assert manager._client is mock_client


async def test_disconnect_clears_client(mock_lr_client):
    manager = _manager_with_client(mock_lr_client)

    await manager.disconnect()

    mock_lr_client.disconnect.assert_awaited_once()
    assert manager._client is None


async def test_disconnect_when_no_client_is_safe():
    manager = ResilientClientManager()
    # _client is None; should not raise
    await manager.disconnect()


async def test_get_client_creates_on_first_call():
    mock_client = _make_client()

    with patch(
        "mcp_server.shared.resilient_client.LightroomClient",
        return_value=mock_client,
    ):
        manager = ResilientClientManager()
        client = await manager.get_client()

    assert client is mock_client
    mock_client.connect.assert_awaited_once()


async def test_get_client_returns_existing_without_reconnecting(mock_lr_client):
    manager = _manager_with_client(mock_lr_client)

    client = await manager.get_client()

    assert client is mock_lr_client
    mock_lr_client.connect.assert_not_awaited()
