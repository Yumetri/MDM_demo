from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.value_objects.country_code import CountryCode
from mdm_demo.domain.value_objects.country_name import CountryName


@dataclass(frozen=True, eq=False)
class Country:
    id: UUID
    name: CountryName
    code: CountryCode
    created_at: datetime
    updated_at: datetime

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Country) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, name: str, code: str) -> "Country":
        country_name = CountryName(name)
        country_code = CountryCode(code)
        now = datetime.now(UTC)
        return cls(uuid4(), country_name, country_code, now, now)

    def rename(self, name: str) -> bool:
        new_name = CountryName(name)
        if new_name == self.name:
            return False
        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str]:
        return {"id": str(self.id), "name": self.name.value, "code": self.code.value}
