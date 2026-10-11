from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.brand_code import BrandCode
from mdm_demo.domain.value_objects.brand_name import BrandName


@dataclass(frozen=True, eq=False)
class Brand:
    id: UUID
    name: BrandName
    code: BrandCode
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Brand) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, name: str, code: str | None = None) -> "Brand":
        brand_name = BrandName(name)
        brand_code = BrandCode.from_name(brand_name) if code is None else BrandCode(code)
        now = datetime.now(UTC)
        return cls(uuid4(), brand_name, brand_code, now, now)

    def rename(self, name: str) -> bool:
        new_name = BrandName(name)
        if new_name == self.name:
            return False
        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str]:
        return {"id": str(self.id), "name": self.name.value, "code": self.code.value}
