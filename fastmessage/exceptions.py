class FastMessageException(Exception):
    pass


class MethodValidationError(Exception):
    pass


class DuplicateCallbackException(FastMessageException):
    pass


class NotAllowedParamKindException(FastMessageException):
    pass


class MissingCallbackException(FastMessageException):
    pass


class SpecialDefaultValueException(FastMessageException):
    pass


class UnnamedCallableException(FastMessageException):
    pass
