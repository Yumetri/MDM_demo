from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.category_code import CategoryCode
from mdm_demo.domain.value_objects.category_name import CategoryName


@dataclass(frozen=True, eq=False)
class Category:
    id: UUID
    name: CategoryName
    code: CategoryCode
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Category) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, name: str, code: str | None = None) -> "Category":
        category_name = CategoryName(name)
        category_code = (
            CategoryCode.from_name(category_name) if code is None else CategoryCode(code)
        )
        now = datetime.now(UTC)
        return cls(uuid4(), category_name, category_code, now, now)

    def rename(self, name: str) -> bool:
        new_name = CategoryName(name)
        if new_name == self.name:
            return False
        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str]:
        return {"id": str(self.id), "name": self.name.value, "code": self.code.value}
