class DatabaseUnavailableError(Exception):
    """Raised when PostgreSQL database is unreachable or connection refused."""
    pass


class UpstreamAPIError(Exception):
    """Raised when an external upstream API call fails or returns invalid response."""
    pass
