"""Application failures mapped to HTTP only by presentation."""


class ApplicationError(Exception):
    def __init__(self, code: str, field: str | None = None) -> None:
        self.code = code
        self.field = field
        super().__init__(code)


class DuplicateCompanyCode(Exception):
    """Persistence port signal for the named company code constraint only."""
