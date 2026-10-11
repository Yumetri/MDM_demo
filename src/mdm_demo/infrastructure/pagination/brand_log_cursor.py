from uuid import UUID

from mdm_demo.application.ports.cursors.brand import BrandBoundary, BrandLogBoundary
from mdm_demo.infrastructure.pagination.brand_cursor import SignedBrandCursor


class SignedBrandLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedBrandCursor(key)
        self._key = key

    def _codec(self, brand_id: UUID) -> SignedBrandCursor:
        return SignedBrandCursor(self._key, query=f"brand_logs:{brand_id}:occurred_at,id:asc")

    def encode(self, boundary: BrandLogBoundary, brand_id: UUID) -> str:
        return self._codec(brand_id).encode(BrandBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, brand_id: UUID) -> BrandLogBoundary:
        boundary = self._codec(brand_id).decode(token)
        return BrandLogBoundary(boundary.created_at, boundary.id)
