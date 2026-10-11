from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CompanyBoundary:
    created_at: datetime
    id: UUID


class CompanyCursor(Protocol):
    def encode(self, boundary: CompanyBoundary) -> str: ...
    def decode(self, token: str) -> CompanyBoundary: ...


@dataclass(frozen=True)
class CompanyLogBoundary:
    occurred_at: datetime
    id: UUID


class CompanyLogCursor(Protocol):
    def encode(self, boundary: CompanyLogBoundary, company_id: UUID) -> str: ...
    def decode(self, token: str, company_id: UUID) -> CompanyLogBoundary: ...


@dataclass(frozen=True)
class ModelBoundary:
    created_at: datetime
    id: UUID


class ModelCursor(Protocol):
    def encode(self, boundary: ModelBoundary) -> str: ...
    def decode(self, token: str) -> ModelBoundary: ...


@dataclass(frozen=True)
class ModelLogBoundary:
    occurred_at: datetime
    id: UUID


class ModelLogCursor(Protocol):
    def encode(self, boundary: ModelLogBoundary, model_id: UUID) -> str: ...
    def decode(self, token: str, model_id: UUID) -> ModelLogBoundary: ...


@dataclass(frozen=True)
class BrandBoundary:
    created_at: datetime
    id: UUID


class BrandCursor(Protocol):
    def encode(self, boundary: BrandBoundary) -> str: ...
    def decode(self, token: str) -> BrandBoundary: ...


@dataclass(frozen=True)
class BrandLogBoundary:
    occurred_at: datetime
    id: UUID


class BrandLogCursor(Protocol):
    def encode(self, boundary: BrandLogBoundary, brand_id: UUID) -> str: ...
    def decode(self, token: str, brand_id: UUID) -> BrandLogBoundary: ...
