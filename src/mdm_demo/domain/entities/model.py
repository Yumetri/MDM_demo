from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.model_code import ModelCode
from mdm_demo.domain.value_objects.model_name import ModelName


@dataclass(frozen=True, eq=False)
class Model:
    id: UUID
    name: ModelName
    code: ModelCode
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Model) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, name: str, code: str | None = None) -> "Model":
        model_name = ModelName(name)
        model_code = ModelCode.from_name(model_name) if code is None else ModelCode(code)
        now = datetime.now(UTC)
        return cls(uuid4(), model_name, model_code, now, now)

    def rename(self, name: str) -> bool:
        new_name = ModelName(name)
        if new_name == self.name:
            return False
        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str]:
        return {"id": str(self.id), "name": self.name.value, "code": self.code.value}
