from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.memory_size import MemorySize


@dataclass(frozen=True, eq=False)
class Memory:
    id: UUID
    size: MemorySize
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Memory) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, capacity: int, unit: str) -> "Memory":
        size = MemorySize(capacity, unit)
        now = datetime.now(UTC)
        return cls(uuid4(), size, now, now)

    def change_size(self, capacity: int, unit: str) -> bool:
        size = MemorySize(capacity, unit)
        if size == self.size:
            return False
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str | int]:
        return {
            "id": str(self.id),
            "capacity": self.size.capacity,
            "unit": self.size.unit,
            "code": self.size.code,
        }
