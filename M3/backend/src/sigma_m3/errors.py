class DomainError(Exception):
    def __init__(self, code, message, status=422, **details):
        super().__init__(message)
        self.code, self.message, self.status, self.details = code, message, status, details
