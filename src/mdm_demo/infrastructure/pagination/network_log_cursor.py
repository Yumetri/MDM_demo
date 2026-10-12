from uuid import UUID

from mdm_demo.application.ports.cursors.network import NetworkBoundary, NetworkLogBoundary
from mdm_demo.infrastructure.pagination.network_cursor import SignedNetworkCursor


class SignedNetworkLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedNetworkCursor(key)
        self._key = key

    def _codec(self, network_id: UUID) -> SignedNetworkCursor:
        return SignedNetworkCursor(
            self._key, query=f"network_logs:{network_id}:occurred_at,id:desc"
        )

    def encode(self, boundary: NetworkLogBoundary, network_id: UUID) -> str:
        return self._codec(network_id).encode(NetworkBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, network_id: UUID) -> NetworkLogBoundary:
        boundary = self._codec(network_id).decode(token)
        return NetworkLogBoundary(boundary.created_at, boundary.id)
