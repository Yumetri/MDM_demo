from dataclasses import dataclass

from mdm_demo.domain.errors import InvalidBrandValue


@dataclass(frozen=True)
class BrandName:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not 1 <= len(value) <= 100 or "\x00" in value:
            raise InvalidBrandValue("name")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidBrandValue("name") from exc
        object.__setattr__(self, "value", value)
