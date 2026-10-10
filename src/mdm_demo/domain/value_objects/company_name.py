from dataclasses import dataclass

from mdm_demo.domain.errors import InvalidCompanyValue


@dataclass(frozen=True)
class CompanyName:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not 1 <= len(value) <= 200 or "\x00" in value:
            raise InvalidCompanyValue("name")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidCompanyValue("name") from exc
        object.__setattr__(self, "value", value)
