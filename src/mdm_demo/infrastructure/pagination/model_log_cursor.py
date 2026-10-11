from uuid import UUID

from mdm_demo.application.ports.cursors.model import ModelBoundary, ModelLogBoundary
from mdm_demo.infrastructure.pagination.model_cursor import SignedModelCursor


class SignedModelLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedModelCursor(key)
        self._key = key

    def _codec(self, model_id: UUID) -> SignedModelCursor:
        return SignedModelCursor(self._key, query=f"model_logs:{model_id}:occurred_at,id:asc")

    def encode(self, boundary: ModelLogBoundary, model_id: UUID) -> str:
        return self._codec(model_id).encode(ModelBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, model_id: UUID) -> ModelLogBoundary:
        boundary = self._codec(model_id).decode(token)
        return ModelLogBoundary(boundary.created_at, boundary.id)
