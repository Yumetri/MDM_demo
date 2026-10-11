import re
from dataclasses import dataclass

from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.model import InvalidModelValue
from mdm_demo.domain.value_objects.model_name import ModelName


@dataclass(frozen=True)
class ModelCode:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9]{3}", self.value.strip()) is None:
            raise InvalidModelValue("code")
        object.__setattr__(self, "value", self.value.strip().upper())

    @classmethod
    def from_name(cls, name: ModelName) -> "ModelCode":
        letters = re.sub(r"[^A-Za-z0-9]", "", name.value)
        if len(letters) < 3:
            raise AutoCodeUnavailable
        return cls(letters[:3])
