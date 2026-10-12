from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.network import Network


@dataclass(frozen=True)
class NetworkDTO:
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, network: Network) -> "NetworkDTO":
        return cls(
            network.id,
            network.name.value,
            network.code.value,
            network.created_at,
            network.updated_at,
        )


@dataclass(frozen=True)
class NetworkPage:
    items: list[NetworkDTO]
    next_cursor: str | None
    has_next: bool
