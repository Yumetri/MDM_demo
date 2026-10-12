from uuid import UUID

from mdm_demo.application.ports.cursors.category import CategoryBoundary, CategoryLogBoundary
from mdm_demo.infrastructure.pagination.category_cursor import SignedCategoryCursor


class SignedCategoryLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedCategoryCursor(key)
        self._key = key

    def _codec(self, category_id: UUID) -> SignedCategoryCursor:
        return SignedCategoryCursor(
            self._key, query=f"category_logs:{category_id}:occurred_at,id:asc"
        )

    def encode(self, boundary: CategoryLogBoundary, category_id: UUID) -> str:
        return self._codec(category_id).encode(CategoryBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, category_id: UUID) -> CategoryLogBoundary:
        boundary = self._codec(category_id).decode(token)
        return CategoryLogBoundary(boundary.created_at, boundary.id)
