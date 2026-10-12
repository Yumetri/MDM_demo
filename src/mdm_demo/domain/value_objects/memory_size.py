from dataclasses import dataclass

from mdm_demo.domain.errors.memory import InvalidMemoryValue


@dataclass(frozen=True)
class MemorySize:
    capacity: int
    unit: str

    def __post_init__(self) -> None:
        if type(self.capacity) is not int or not 1 <= self.capacity <= 2_147_483_647:
            raise InvalidMemoryValue("capacity")
        if not isinstance(self.unit, str):
            raise InvalidMemoryValue("unit")
        unit = self.unit.strip().upper()
        if unit not in {"GB", "TB"}:
            raise InvalidMemoryValue("unit")
        object.__setattr__(self, "unit", unit)

    @property
    def code(self) -> str:
        return f"{self.capacity}{self.unit}"

    @property
    def capacity_gb(self) -> int:
        return self.capacity * (1000 if self.unit == "TB" else 1)
