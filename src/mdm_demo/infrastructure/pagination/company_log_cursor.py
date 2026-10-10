from uuid import UUID

from mdm_demo.application.ports.cursor import CompanyBoundary, CompanyLogBoundary
from mdm_demo.infrastructure.pagination.company_cursor import SignedCompanyCursor


class SignedCompanyLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedCompanyCursor(key)
        self._key = key

    def _codec(self, company_id: UUID) -> SignedCompanyCursor:
        return SignedCompanyCursor(self._key, query=f"company_logs:{company_id}:occurred_at,id:asc")

    def encode(self, boundary: CompanyLogBoundary, company_id: UUID) -> str:
        return self._codec(company_id).encode(CompanyBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, company_id: UUID) -> CompanyLogBoundary:
        boundary = self._codec(company_id).decode(token)
        return CompanyLogBoundary(boundary.created_at, boundary.id)
