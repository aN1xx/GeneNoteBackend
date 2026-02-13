"""ACMG variant classification enumeration."""

from enum import StrEnum


class ACMGClassification(StrEnum):
    """ACMG/AMP variant classification standards.

    Based on Richards et al. 2015 guidelines for interpretation
    of sequence variants.
    """

    PATHOGENIC = "Патогенный"
    LIKELY_PATHOGENIC = "Вероятно патогенный"
    VUS = "Вариант неясного значения"  # Variant of Uncertain Significance
    LIKELY_BENIGN = "Вероятно доброкачественный"
    BENIGN = "Доброкачественный"
    NOT_CLASSIFIED = "Не классифицирован"

    def is_pathogenic(self) -> bool:
        """Check if variant is pathogenic or likely pathogenic."""
        return self in (ACMGClassification.PATHOGENIC, ACMGClassification.LIKELY_PATHOGENIC)

    def is_benign(self) -> bool:
        """Check if variant is benign or likely benign."""
        return self in (ACMGClassification.BENIGN, ACMGClassification.LIKELY_BENIGN)

    def is_uncertain(self) -> bool:
        """Check if variant classification is uncertain."""
        return self in (ACMGClassification.VUS, ACMGClassification.NOT_CLASSIFIED)

    @classmethod
    def from_string(cls, value: str | None) -> "ACMGClassification":
        """Parse ACMG classification from string."""
        if value is None or value.strip() == "":
            return cls.NOT_CLASSIFIED

        value_lower = value.lower().strip()

        # Russian mappings
        if "патогенный" in value_lower:
            if "вероятно" in value_lower:
                return cls.LIKELY_PATHOGENIC
            return cls.PATHOGENIC
        if "доброкачественный" in value_lower:
            if "вероятно" in value_lower:
                return cls.LIKELY_BENIGN
            return cls.BENIGN
        if "неясн" in value_lower or "vus" in value_lower:
            return cls.VUS

        # English mappings
        if "pathogenic" in value_lower:
            if "likely" in value_lower:
                return cls.LIKELY_PATHOGENIC
            return cls.PATHOGENIC
        if "benign" in value_lower:
            if "likely" in value_lower:
                return cls.LIKELY_BENIGN
            return cls.BENIGN

        return cls.NOT_CLASSIFIED
