"""
Unit tests for mcp_server.servers.develop.basic_tools

The tools under test are registered via setup_basic_tools(server, execute_command).
We pass an AsyncMock as execute_command so no Lightroom connection is needed.

Accessing tools: FastMCP.get_tool(name) is a coroutine that returns a
FunctionTool; call its .fn attribute directly in tests.
"""
from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from mcp_server.servers.develop.basic_tools import setup_basic_tools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def execute_cmd() -> AsyncMock:
    """Default execute_command stub; returns a photoId result."""
    return AsyncMock(return_value={"photoId": "photo-99"})


@pytest.fixture
def develop_server(execute_cmd) -> FastMCP:
    """Fresh FastMCP server with basic tools registered."""
    s = FastMCP("test-develop")
    setup_basic_tools(s, execute_cmd)
    return s


async def _get_tool_fn(server: FastMCP, name: str):
    """Await get_tool() and return the underlying callable."""
    tool = await server.get_tool(name)
    return tool.fn


# ---------------------------------------------------------------------------
# develop_adjust_exposure — range validation and response shaping
# ---------------------------------------------------------------------------

async def test_exposure_valid_positive(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    result = await fn(value=1.5)
    assert result["success"] is True
    assert result["parameter"] == "Exposure"
    assert result["value"] == 1.5


async def test_exposure_valid_negative(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    result = await fn(value=-2.0)
    assert result["success"] is True


async def test_exposure_valid_zero(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    result = await fn(value=0.0)
    assert result["success"] is True


async def test_exposure_at_max_boundary(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    result = await fn(value=5.0)
    assert result["success"] is True


async def test_exposure_at_min_boundary(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    result = await fn(value=-5.0)
    assert result["success"] is True


async def test_exposure_too_high_raises(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    with pytest.raises(ValueError):
        await fn(value=10.0)
    execute_cmd.assert_not_awaited()


async def test_exposure_too_low_raises(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    with pytest.raises(ValueError):
        await fn(value=-99.0)
    execute_cmd.assert_not_awaited()


async def test_exposure_passes_photo_id_when_provided(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    await fn(value=0.5, photo_id="my-photo")
    sent_params = execute_cmd.call_args[0][1]
    assert sent_params["photoId"] == "my-photo"


async def test_exposure_omits_photo_id_when_not_provided(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    await fn(value=0.5)
    sent_params = execute_cmd.call_args[0][1]
    assert "photoId" not in sent_params


async def test_exposure_returns_photo_id_from_result(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_exposure")
    result = await fn(value=1.0)
    assert result["photo_id"] == "photo-99"


# ---------------------------------------------------------------------------
# develop_adjust_contrast — spot-check a dynamically-created tool
# ---------------------------------------------------------------------------

async def test_contrast_valid_range(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_contrast")
    result = await fn(value=50.0)
    assert result["success"] is True
    assert result["parameter"] == "Contrast"


async def test_contrast_out_of_range_raises(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_contrast")
    with pytest.raises(ValueError):
        await fn(value=200.0)


async def test_contrast_boundary_negative(develop_server, execute_cmd):
    fn = await _get_tool_fn(develop_server, "develop_adjust_contrast")
    result = await fn(value=-100.0)
    assert result["success"] is True


# ---------------------------------------------------------------------------
# develop_set_parameters — Temperature/Tint separation logic
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_selected_client() -> AsyncMock:
    """Async client that reports 1 selected photo."""
    client = AsyncMock()
    client.execute_command = AsyncMock(
        return_value={"count": 1, "photos": [{"id": "photo-99"}]}
    )
    return client


@pytest.fixture
def server_with_selection(execute_cmd, mock_selected_client, monkeypatch) -> FastMCP:
    """
    Server whose internal _check_photo_selection reports a selected photo.
    Patches resilient_client_manager at the import location used by basic_tools.
    """
    mock_manager = AsyncMock()
    mock_manager.get_client = AsyncMock(return_value=mock_selected_client)

    monkeypatch.setattr(
        "mcp_server.shared.resilient_client.resilient_client_manager",
        mock_manager,
    )

    s = FastMCP("test-develop-with-selection")
    setup_basic_tools(s, execute_cmd)
    return s


async def test_set_parameters_sends_temperature_via_setvalue(server_with_selection, execute_cmd):
    """Temperature must NOT go through applySettings; it uses setValue."""
    fn = await _get_tool_fn(server_with_selection, "develop_set_parameters")
    await fn(settings={"Contrast": 30, "Temperature": 5500})

    apply_calls = [c for c in execute_cmd.call_args_list if c[0][0] == "applySettings"]
    setval_calls = [c for c in execute_cmd.call_args_list if c[0][0] == "setValue"]

    for c in apply_calls:
        assert "Temperature" not in c[0][1].get("settings", {}), \
            "Temperature should NOT appear in applySettings payload"

    assert any(c[0][1].get("param") == "Temperature" for c in setval_calls), \
        "Temperature should be sent via setValue"


async def test_set_parameters_sends_tint_via_setvalue(server_with_selection, execute_cmd):
    """Tint must NOT go through applySettings; it uses setValue."""
    fn = await _get_tool_fn(server_with_selection, "develop_set_parameters")
    await fn(settings={"Tint": -10})

    setval_calls = [c for c in execute_cmd.call_args_list if c[0][0] == "setValue"]
    assert any(c[0][1].get("param") == "Tint" for c in setval_calls), \
        "Tint should be sent via setValue"


async def test_set_parameters_rejects_out_of_range_exposure(server_with_selection, execute_cmd):
    fn = await _get_tool_fn(server_with_selection, "develop_set_parameters")
    result = await fn(settings={"Exposure": 99.0})  # max is 5
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAM_VALUE"


async def test_set_parameters_no_photo_returns_structured_error(execute_cmd, monkeypatch):
    """When no photo is selected the tool returns a structured error dict (not an exception)."""
    mock_client = AsyncMock()
    mock_client.execute_command = AsyncMock(return_value={"count": 0, "photos": []})
    mock_manager = AsyncMock()
    mock_manager.get_client = AsyncMock(return_value=mock_client)

    monkeypatch.setattr(
        "mcp_server.shared.resilient_client.resilient_client_manager",
        mock_manager,
    )

    s = FastMCP("test-no-photo")
    setup_basic_tools(s, execute_cmd)

    fn = await _get_tool_fn(s, "develop_set_parameters")
    result = await fn(settings={"Contrast": 10})

    assert result["success"] is False
    assert result["error"]["code"] == "NO_PHOTO_SELECTED"
    execute_cmd.assert_not_awaited()


# ---------------------------------------------------------------------------
# develop_set_parameter — generic single-param tool
# ---------------------------------------------------------------------------

async def test_set_parameter_rejects_out_of_range_contrast(server_with_selection, execute_cmd):
    fn = await _get_tool_fn(server_with_selection, "develop_set_parameter")
    result = await fn(parameter="Contrast", value=500)
    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PARAM_VALUE"


async def test_set_parameter_accepts_valid_value(server_with_selection, execute_cmd):
    execute_cmd.return_value = {"photoId": "photo-99"}
    fn = await _get_tool_fn(server_with_selection, "develop_set_parameter")
    result = await fn(parameter="Contrast", value=50)
    assert result["success"] is True
    assert result["parameter"] == "Contrast"
    assert result["value"] == 50
