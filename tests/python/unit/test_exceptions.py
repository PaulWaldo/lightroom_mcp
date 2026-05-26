"""
Unit tests for lightroom_sdk.exceptions

Tests exercise the exception hierarchy, default messages, error codes, and the
ERROR_CODE_MAP dispatch table — all without any network or socket dependency.
"""
import pytest

from lightroom_sdk.exceptions import (
    CatalogAccessError,
    ConnectionError,
    ERROR_CODE_MAP,
    HandlerError,
    LightroomSDKError,
    ParameterError,
    ParameterOutOfRangeError,
    PhotoNotFoundError,
    PhotoNotSelectedError,
    ResourceUnavailableError,
    TimeoutError,
    WriteAccessBlockedError,
)


# ---------------------------------------------------------------------------
# LightroomSDKError — base class
# ---------------------------------------------------------------------------

def test_sdk_error_message_stored():
    exc = LightroomSDKError("something went wrong")
    assert str(exc) == "something went wrong"


def test_sdk_error_code_defaults_to_none():
    assert LightroomSDKError("msg").code is None


def test_sdk_error_details_defaults_to_empty_dict():
    assert LightroomSDKError("msg").details == {}


def test_sdk_error_code_and_details_stored():
    exc = LightroomSDKError("msg", code="FOO", details={"key": "val"})
    assert exc.code == "FOO"
    assert exc.details == {"key": "val"}


def test_sdk_error_is_exception_subclass():
    assert issubclass(LightroomSDKError, Exception)


# ---------------------------------------------------------------------------
# PhotoNotSelectedError
# ---------------------------------------------------------------------------

def test_photo_not_selected_default_message():
    assert "select a photo" in str(PhotoNotSelectedError()).lower()


def test_photo_not_selected_default_code():
    assert PhotoNotSelectedError().code == "NO_PHOTO_SELECTED"


def test_photo_not_selected_custom_message():
    assert str(PhotoNotSelectedError("pick one first")) == "pick one first"


def test_photo_not_selected_is_sdk_error():
    assert isinstance(PhotoNotSelectedError(), LightroomSDKError)


# ---------------------------------------------------------------------------
# ParameterOutOfRangeError
# ---------------------------------------------------------------------------

def test_out_of_range_auto_builds_message():
    exc = ParameterOutOfRangeError(param="Exposure", value=10.0, min_val=-5.0, max_val=5.0)
    msg = str(exc)
    assert "Exposure" in msg
    assert "10.0" in msg
    assert "-5.0" in msg
    assert "5.0" in msg


def test_out_of_range_explicit_message_overrides_auto():
    assert str(ParameterOutOfRangeError(message="custom msg")) == "custom msg"


def test_out_of_range_default_code():
    exc = ParameterOutOfRangeError(param="Contrast", value=200, min_val=-100, max_val=100)
    assert exc.code == "INVALID_PARAM_VALUE"


def test_out_of_range_no_args_uses_generic_message():
    assert str(ParameterOutOfRangeError()) != ""


def test_out_of_range_is_parameter_error():
    assert isinstance(ParameterOutOfRangeError(), ParameterError)


def test_out_of_range_is_sdk_error():
    assert isinstance(ParameterOutOfRangeError(), LightroomSDKError)


# ---------------------------------------------------------------------------
# PhotoNotFoundError
# ---------------------------------------------------------------------------

def test_photo_not_found_includes_id_in_message():
    assert "abc-123" in str(PhotoNotFoundError(photo_id="abc-123"))


def test_photo_not_found_default_code():
    assert PhotoNotFoundError(photo_id="x").code == "PHOTO_NOT_FOUND"


def test_photo_not_found_no_args_generic_message():
    assert str(PhotoNotFoundError()) != ""


# ---------------------------------------------------------------------------
# Convenience exception defaults
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cls, expected_code",
    [
        (CatalogAccessError, "CATALOG_ACCESS_FAILED"),
        (WriteAccessBlockedError, "WRITE_ACCESS_BLOCKED"),
        (ResourceUnavailableError, "RESOURCE_UNAVAILABLE"),
    ],
)
def test_convenience_exception_default_code(cls, expected_code):
    assert cls().code == expected_code


def test_handler_error_stores_message_and_code():
    exc = HandlerError("lua blew up")
    assert str(exc) == "lua blew up"
    assert exc.code == "HANDLER_ERROR"


def test_connection_error_is_sdk_error():
    assert isinstance(ConnectionError("lost"), LightroomSDKError)


def test_timeout_error_is_sdk_error():
    assert isinstance(TimeoutError("timed out"), LightroomSDKError)


# ---------------------------------------------------------------------------
# ERROR_CODE_MAP dispatch table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code, expected_cls",
    [
        ("NO_PHOTO_SELECTED", PhotoNotSelectedError),
        ("MISSING_PHOTO_ID", PhotoNotSelectedError),
        ("PHOTO_NOT_FOUND", PhotoNotFoundError),
        ("INVALID_PARAM", ParameterError),
        ("INVALID_PARAM_VALUE", ParameterOutOfRangeError),
        ("INVALID_PARAM_TYPE", ParameterError),
        ("HANDLER_ERROR", HandlerError),
        ("CONNECTION_FAILED", ConnectionError),
        ("CATALOG_ACCESS_FAILED", CatalogAccessError),
        ("WRITE_ACCESS_BLOCKED", WriteAccessBlockedError),
        ("RESOURCE_UNAVAILABLE", ResourceUnavailableError),
    ],
)
def test_error_code_map_known_code(code, expected_cls):
    assert ERROR_CODE_MAP[code] is expected_cls


def test_error_code_map_unknown_code_falls_back_to_base():
    cls = ERROR_CODE_MAP.get("TOTALLY_MADE_UP", LightroomSDKError)
    assert cls is LightroomSDKError


def test_error_code_map_raises_correct_exception_type():
    """Simulate what LightroomClient does when it receives an error response."""
    code = "NO_PHOTO_SELECTED"
    exc_cls = ERROR_CODE_MAP.get(code, LightroomSDKError)
    with pytest.raises(PhotoNotSelectedError):
        raise exc_cls("no photo", code=code, details={})
