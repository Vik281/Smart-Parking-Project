class ServiceError(Exception):
    """Business-rule failure. The API layer turns these into HTTP responses,
    so services never need to know about HTTP status codes."""

    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFoundError(ServiceError):
    status_code = 404


class ConflictError(ServiceError):
    status_code = 409
