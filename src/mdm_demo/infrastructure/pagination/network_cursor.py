import base64
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import UUID

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.network import NetworkBoundary


class SignedNetworkCursor:
    _query = "networks:created_at,id:desc"

    def __init__(self, key: str, *, query: str = "networks:created_at,id:desc") -> None:
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
        if SignedNetworkCursor._encode(result) != data:
            raise ValueError("Noncanonical encoding")
        return result

    def encode(self, boundary: NetworkBoundary) -> str:
        data = json.dumps(
            {
                "v": 1,
                "q": self._query,
                "t": boundary.created_at.astimezone(UTC).isoformat(),
                "id": str(boundary.id),
            },
            separators=(",", ":"),
        ).encode()
        signature = hmac.digest(self._key, data, hashlib.sha256)
        return self._encode(data) + "." + self._encode(signature)

    def decode(self, token: str) -> NetworkBoundary:
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
            if not isinstance(value, dict) or set(value) != {"v", "q", "t", "id"}:
                raise ValueError("Invalid shape")
            if type(value["v"]) is not int or value["v"] != 1 or value["q"] != self._query:
                raise ValueError("Invalid context")
            created_at = datetime.fromisoformat(value["t"])
            if created_at.tzinfo is None:
                raise ValueError("Missing timezone")
            return NetworkBoundary(created_at.astimezone(UTC), UUID(value["id"]))
        except (ValueError, TypeError, KeyError, AttributeError, binascii.Error) as exc:
            raise ApplicationError("INVALID_CURSOR") from exc
