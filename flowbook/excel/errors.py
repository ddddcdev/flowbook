class ExcelError(Exception):
    pass


class ExcelTableError(ExcelError):
    pass


class MissingRequiredColumnsError(ExcelTableError):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing required columns: {missing}")
        self.missing = missing
