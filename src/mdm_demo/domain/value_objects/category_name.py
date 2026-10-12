from dataclasses import dataclass
from unicodedata import normalize

from mdm_demo.domain.errors.category import InvalidCategoryValue


@dataclass(frozen=True)
class CategoryName:
    value: str

    def __post_init__(self) -> None:
        value = normalize("NFC", self.value.strip().upper())
        if not 1 <= len(value) <= 100 or "\x00" in value:
            raise InvalidCategoryValue("name")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidCategoryValue("name") from exc
        object.__setattr__(self, "value", value)
