"""
Unit tests for lightroom_sdk.protocol

Verifies that the Pydantic models correctly validate, serialise, and reject
malformed data — no socket or Lightroom connection required.
"""
import pytest
from pydantic import ValidationError

from lightroom_sdk.protocol import LightroomError, LightroomRequest, LightroomResponse


# ---------------------------------------------------------------------------
# LightroomRequest
# ---------------------------------------------------------------------------

def test_request_minimal_valid():
    req = LightroomRequest(id="req-1", command="system.ping")
    assert req.id == "req-1"
    assert req.command == "system.ping"
    assert req.params == {}  # default_factory produces empty dict


def test_request_params_stored():
    req = LightroomRequest(id="r", command="develop.setValue", params={"param": "Exposure", "value": 0.5})
    assert req.params["param"] == "Exposure"
    assert req.params["value"] == 0.5


def test_request_timestamp_defaults_to_none():
    assert LightroomRequest(id="r", command="ping").timestamp is None


def test_request_timestamp_accepted():
    req = LightroomRequest(id="r", command="ping", timestamp=1_700_000_000)
    assert req.timestamp == 1_700_000_000


def test_request_missing_id_raises():
    with pytest.raises(ValidationError):
        LightroomRequest(command="ping")  # type: ignore[call-arg]


def test_request_missing_command_raises():
    with pytest.raises(ValidationError):
        LightroomRequest(id="r")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# LightroomResponse
# ---------------------------------------------------------------------------

def test_response_success():
    resp = LightroomResponse(id="r1", success=True, result={"photoId": "p-1"})
    assert resp.success is True
    assert resp.result == {"photoId": "p-1"}
    assert resp.error is None


def test_response_error():
    resp = LightroomResponse(
        id="r1",
        success=False,
        error={"code": "NO_PHOTO_SELECTED", "message": "pick a photo"},
    )
    assert resp.success is False
    assert resp.error["code"] == "NO_PHOTO_SELECTED"
    assert resp.result is None


def test_response_result_and_error_both_optional():
    resp = LightroomResponse(id="r", success=True)
    assert resp.result is None
    assert resp.error is None


def test_response_missing_id_raises():
    with pytest.raises(ValidationError):
        LightroomResponse(success=True)  # type: ignore[call-arg]


def test_response_missing_success_raises():
    with pytest.raises(ValidationError):
        LightroomResponse(id="r")  # type: ignore[call-arg]


def test_response_roundtrip_serialisation():
    original = LightroomResponse(id="r", success=True, result={"k": "v"})
    restored = LightroomResponse.model_validate(original.model_dump())
    assert restored.id == original.id
    assert restored.result == original.result


# ---------------------------------------------------------------------------
# LightroomError
# ---------------------------------------------------------------------------

def test_error_minimal_valid():
    err = LightroomError(code="FOO", message="something failed")
    assert err.code == "FOO"
    assert err.message == "something failed"
    assert err.severity == "error"  # default


def test_error_custom_severity():
    err = LightroomError(code="WARN", message="watch out", severity="warning")
    assert err.severity == "warning"


def test_error_details_defaults_to_none():
    assert LightroomError(code="X", message="y").details is None


def test_error_details_accepted():
    err = LightroomError(code="X", message="y", details={"hint": "try again"})
    assert err.details == {"hint": "try again"}


def test_error_missing_code_raises():
    with pytest.raises(ValidationError):
        LightroomError(message="oops")  # type: ignore[call-arg]


def test_error_missing_message_raises():
    with pytest.raises(ValidationError):
        LightroomError(code="X")  # type: ignore[call-arg]
