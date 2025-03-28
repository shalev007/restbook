class AuthenticationError(Exception):
    pass

class RetryableError(Exception):
    pass

class RetryExceededError(Exception):
    pass

class UnknownError(Exception):
    pass

class SSLVerificationError(Exception):
    pass

class JSONError(Exception):
    pass