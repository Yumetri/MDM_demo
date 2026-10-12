import base64
import binascii
import hashlib
import hmac
import json

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.year import YearBoundary


class SignedYearCursor:
    _query = "years:year:desc"

    def __init__(self, key: str, *, query: str = "years:year:desc") -> None:
        if len(key.encode()) < 32:
            raise ValueError("CURSOR_SIGNING_KEY must contain at least 32 bytes")
        self._key = key.encode()
        self._query = query

    @staticmethod
    def _encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(data: str) -> bytes:
        result = base64.b64decode(data + "=" * (-len(data) % 4), altchars=b"-_", validate=True)
        if SignedYearCursor._encode(result) != data:
            raise ValueError("Noncanonical encoding")
        return result

    def encode(self, boundary: YearBoundary) -> str:
        data = json.dumps(
            {
                "v": 1,
                "q": self._query,
                "year": boundary.year,
            },
            separators=(",", ":"),
        ).encode()
        signature = hmac.digest(self._key, data, hashlib.sha256)
        return self._encode(data) + "." + self._encode(signature)

    def decode(self, token: str) -> YearBoundary:
        try:
            if len(token) > 2048:
                raise ValueError("Too long")
            payload, signature = token.split(".")
            data = self._decode(payload)
            if not hmac.compare_digest(
                self._decode(signature), hmac.digest(self._key, data, hashlib.sha256)
            ):
                raise ValueError("Invalid signature")
            value = json.loads(data)
            if not isinstance(value, dict) or set(value) != {"v", "q", "year"}:
                raise ValueError("Invalid shape")
            if type(value["v"]) is not int or value["v"] != 1 or value["q"] != self._query:
                raise ValueError("Invalid context")
            year = value["year"]
            if type(year) is not int or not 1900 <= year <= 2999:
                raise ValueError("Invalid year boundary")
            return YearBoundary(year)
        except (ValueError, TypeError, KeyError, AttributeError, binascii.Error) as exc:
            raise ApplicationError("INVALID_CURSOR") from exc
