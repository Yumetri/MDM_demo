class DuplicateCountryCode(Exception):
    """Persistence port signal for the country code UNIQUE constraint."""


class DuplicateCountryName(Exception):
    """Persistence port signal for the country name UNIQUE constraint."""
