from uuid import UUID

from mdm_demo.application.ports.cursor import CountryBoundary, CountryLogBoundary
from mdm_demo.infrastructure.pagination.country_cursor import SignedCountryCursor


class SignedCountryLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedCountryCursor(key)
        self._key = key

    def _codec(self, country_id: UUID) -> SignedCountryCursor:
        return SignedCountryCursor(self._key, query=f"country_logs:{country_id}:occurred_at,id:asc")

    def encode(self, boundary: CountryLogBoundary, country_id: UUID) -> str:
        return self._codec(country_id).encode(CountryBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, country_id: UUID) -> CountryLogBoundary:
        boundary = self._codec(country_id).decode(token)
        return CountryLogBoundary(boundary.created_at, boundary.id)
