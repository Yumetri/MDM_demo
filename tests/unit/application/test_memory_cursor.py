import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.memory import MemoryBoundary
from mdm_demo.infrastructure.pagination.memory_cursor import SignedMemoryCursor


def test_round_trip_and_key_rotation(memory_cursor_codec):
    boundary = MemoryBoundary(datetime.now(UTC), uuid4())
    token = memory_cursor_codec.encode(boundary)
    assert memory_cursor_codec.decode(token) == boundary
    with pytest.raises(ApplicationError):
        SignedMemoryCursor("different-key-with-at-least-32-bytes").decode(token)


@pytest.mark.parametrize("token", ["", "x", "a.b", "a.b.c", "한글.서명", "a" * 2049])
def test_malformed_cursor(memory_cursor_codec, token):
    with pytest.raises(ApplicationError) as error:
        memory_cursor_codec.decode(token)
    assert error.value.code == "INVALID_CURSOR"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("v", 2),
        ("v", True),
        ("q", "another-query"),
        ("t", "2026-10-10T00:00:00"),
        ("t", "not-a-date"),
        ("id", "invalid-uuid"),
    ],
)
def test_signed_but_invalid_payload(memory_cursor_codec, field, value):
    data = {
        "v": 1,
        "q": "memories:created_at,id:asc",
        "t": datetime.now(UTC).isoformat(),
        "id": str(uuid4()),
    }
    data[field] = value
    payload = json.dumps(data).encode()

    def encode(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    token = (
        encode(payload)
        + "."
        + encode(
            hmac.digest(b"test-only-signing-key-with-at-least-32-bytes", payload, hashlib.sha256)
        )
    )
    with pytest.raises(ApplicationError):
        memory_cursor_codec.decode(token)


def test_key_required():
    with pytest.raises(ValueError):
        SignedMemoryCursor("")
