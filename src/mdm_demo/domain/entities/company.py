from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.company_code import CompanyCode
from mdm_demo.domain.value_objects.company_name import CompanyName


@dataclass(frozen=True, eq=False)
class Company:
    id: UUID
    name: CompanyName
    code: CompanyCode
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Company) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, name: str, code: str | None = None) -> "Company":
        company_name = CompanyName(name)
        company_code = CompanyCode.from_name(company_name) if code is None else CompanyCode(code)
        now = datetime.now(UTC)
        return cls(uuid4(), company_name, company_code, now, now)

    def rename(self, name: str) -> bool:
        new_name = CompanyName(name)
        if new_name == self.name:
            return False
        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str]:
        return {"id": str(self.id), "name": self.name.value, "code": self.code.value}
