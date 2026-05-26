"""
Shared pytest fixtures for mcp_server unit tests.

All fixtures here provide mock/stub versions of the Lightroom connection layer so
tests can run without Lightroom Classic being open.
"""
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Low-level execute_command stand-in
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_execute() -> AsyncMock:
    """
    An AsyncMock that replaces the ``execute_command`` callable passed into
    ``setup_*_tools()`` functions (e.g. ``setup_basic_tools(server, execute_command)``).

    By default it returns ``{"photoId": "photo-42"}``.  Override the return
    value inside individual tests::

        mock_execute.return_value = {"count": 2, "photos": [...]}
    """
    return AsyncMock(return_value={"photoId": "photo-42"})


# ---------------------------------------------------------------------------
# ResilientClientManager mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_resilient_manager() -> MagicMock:
    """
    A MagicMock that replaces the global ``resilient_client_manager``.

    The ``execute_with_retry`` coroutine returns ``{"photoId": "photo-42"}``
    by default; override per test as needed.
    """
    manager = MagicMock()
    manager.execute_with_retry = AsyncMock(return_value={"photoId": "photo-42"})
    manager.get_client = AsyncMock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    return manager


@pytest.fixture
def patched_resilient_manager(mock_resilient_manager, monkeypatch):
    """
    Same as ``mock_resilient_manager`` but also patches the module-level
    globals so class-based servers (CatalogServer, SystemServer …) pick it up.
    """
    monkeypatch.setattr(
        "mcp_server.shared.resilient_client.resilient_client_manager",
        mock_resilient_manager,
    )
    monkeypatch.setattr(
        "mcp_server.shared.base.resilient_client_manager",
        mock_resilient_manager,
    )
    return mock_resilient_manager


# ---------------------------------------------------------------------------
# LightroomClient mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_lr_client() -> MagicMock:
    """
    A minimal mock of ``LightroomClient`` for use in resilient-client tests.
    """
    client = MagicMock()
    client.execute_command = AsyncMock(return_value={"photoId": "photo-42"})
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.ping = AsyncMock(return_value={"message": "pong"})
    return client
