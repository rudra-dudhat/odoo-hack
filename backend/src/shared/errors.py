class BusinessRuleError(Exception):
    """Base class for all business rule exceptions."""
    def __init__(self, message: str, code: str = "BUSINESS_RULE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class NotFoundError(BusinessRuleError):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str, code: str = "NOT_FOUND"):
        super().__init__(message, code)

class ConflictError(BusinessRuleError):
    """Exception raised when a business rule conflict occurs."""
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(message, code)

class ValidationError(BusinessRuleError):
    """Exception raised when validation fails."""
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", field_errors: list = None):
        super().__init__(message, code)
        self.field_errors = field_errors or []

class ForbiddenError(BusinessRuleError):
    """Exception raised when a request is forbidden."""
    def __init__(self, message: str, code: str = "FORBIDDEN"):
        super().__init__(message, code)

class UnauthenticatedError(BusinessRuleError):
    """Exception raised when a request is unauthenticated."""
    def __init__(self, message: str, code: str = "UNAUTHENTICATED"):
        super().__init__(message, code)

# Specific Domain Exceptions
class AllocationConflictError(ConflictError):
    def __init__(self, message: str):
        super().__init__(message, "ALLOCATION_CONFLICT")

class BookingOverlapError(ConflictError):
    def __init__(self, message: str):
        super().__init__(message, "BOOKING_OVERLAP")
