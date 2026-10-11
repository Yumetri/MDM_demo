from mdm_demo.domain.errors import DomainError


class InvalidModelValue(DomainError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(field)
