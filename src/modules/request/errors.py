import aiohttp


class AuthenticationError(Exception):
    pass

class RetryableError(Exception):
    pass

class RateLimitError(Exception):
    def __init__(self, response: aiohttp.ClientResponse):
        self.response = response
        super().__init__(f"Rate limit exceeded: {response.status}")

class RetryExceededError(Exception):
    pass

class UnknownError(Exception):
    pass

class SSLVerificationError(Exception):
    pass