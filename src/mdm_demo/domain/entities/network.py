from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.network_code import NetworkCode
from mdm_demo.domain.value_objects.network_name import NetworkName


@dataclass(frozen=True, eq=False)
class Network:
    id: UUID
    name: NetworkName
    code: NetworkCode
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Network) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, name: str, code: str | None = None) -> "Network":
        network_name = NetworkName(name)
        network_code = NetworkCode.from_name(network_name) if code is None else NetworkCode(code)
        now = datetime.now(UTC)
        return cls(uuid4(), network_name, network_code, now, now)

    def rename(self, name: str) -> bool:
        new_name = NetworkName(name)
        if new_name == self.name:
            return False
        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str]:
        return {"id": str(self.id), "name": self.name.value, "code": self.code.value}
