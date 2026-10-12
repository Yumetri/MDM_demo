import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.year import YearBoundary, YearLogBoundary
from mdm_demo.infrastructure.pagination.year_cursor import SignedYearCursor
from mdm_demo.infrastructure.pagination.year_log_cursor import SignedYearLogCursor


def signed(codec, key, value):
    data = json.dumps(value, separators=(",", ":")).encode()
    return (
        codec._encode(data) + "." + codec._encode(hmac.digest(key.encode(), data, hashlib.sha256))
    )


@pytest.mark.parametrize("value", [True, 2024.0, "2024", 1899, 3000, None])
def test_year_boundary_rejects_signed_wrong_types_and_range(signing_key, value):
    codec = SignedYearCursor(signing_key)
    token = signed(codec, signing_key, {"v": 1, "q": "years:year:desc", "year": value})
    with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
        codec.decode(token)


def test_cursor_context_and_tampering(signing_key):
    year = SignedYearCursor(signing_key)
    log = SignedYearLogCursor(signing_key)
    target = uuid4()
    assert year.decode(year.encode(YearBoundary(2024))) == YearBoundary(2024)
    boundary = YearLogBoundary(datetime.now(UTC), uuid4())
    token = log.encode(boundary, target)
    assert log.decode(token, target) == boundary
    for invalid in ["", "bad", token + "x", "x" * 2049]:
        with pytest.raises(ApplicationError):
            log.decode(invalid, target)
    with pytest.raises(ApplicationError):
        log.decode(token, uuid4())
    with pytest.raises(ApplicationError):
        year.decode(token)
    with pytest.raises(ApplicationError):
        log.decode(year.encode(YearBoundary(2024)), target)
    with pytest.raises(ValueError):
        SignedYearCursor("short")
    with pytest.raises(ValueError):
        SignedYearLogCursor("short")
