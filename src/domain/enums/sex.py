"""Sex enumeration."""

from enum import StrEnum


class Sex(StrEnum):
    """Biological sex of a patient."""

    MALE = "м"
    FEMALE = "ж"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "Sex":
        """Parse sex from string (case-insensitive)."""
        value_lower = value.lower().strip()
        if value_lower in ("м", "m", "male", "мужской"):
            return cls.MALE
        if value_lower in ("ж", "f", "female", "женский"):
            return cls.FEMALE
        return cls.UNKNOWN
