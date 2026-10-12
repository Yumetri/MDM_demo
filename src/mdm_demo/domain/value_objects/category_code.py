import re
from dataclasses import dataclass

from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.category import InvalidCategoryValue
from mdm_demo.domain.value_objects.category_name import CategoryName


@dataclass(frozen=True)
class CategoryCode:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9]{3}", self.value.strip()) is None:
            raise InvalidCategoryValue("code")
        object.__setattr__(self, "value", self.value.strip().upper())

    @classmethod
    def from_name(cls, name: CategoryName) -> "CategoryCode":
        letters = re.sub(r"[^A-Za-z0-9]", "", name.value)
        if len(letters) < 3:
            raise AutoCodeUnavailable
        return cls(letters[:3])
