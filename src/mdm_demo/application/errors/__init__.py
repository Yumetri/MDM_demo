class ApplicationError(Exception):
    def __init__(self, code: str, field: str | None = None, *, dimension: str = "company") -> None:
        self.dimension = dimension
        self.code = code
        self.field = field
        super().__init__(code)
