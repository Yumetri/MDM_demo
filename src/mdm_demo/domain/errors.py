"""Business errors, independent of HTTP and storage."""


class DomainError(Exception):
    pass


class InvalidCompanyValue(DomainError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(field)


class AutoCodeUnavailable(DomainError):
    pass
