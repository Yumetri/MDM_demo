from dataclasses import dataclass

from mdm_demo.domain.errors.model import InvalidModelValue


@dataclass(frozen=True)
class ModelName:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not 1 <= len(value) <= 100 or "\x00" in value:
            raise InvalidModelValue("name")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidModelValue("name") from exc
        object.__setattr__(self, "value", value)
