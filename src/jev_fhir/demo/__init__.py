"""Optional demo API foundations and shared errors."""


class DemoNotFoundError(LookupError):
    """Raised when a demo request references an item outside the fixture allow-list."""
