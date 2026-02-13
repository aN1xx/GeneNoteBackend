"""Variant type enumeration."""

from enum import StrEnum


class VariantType(StrEnum):
    """Types of genetic variants."""

    # SNV - Single Nucleotide Variant
    SNV = "SNV"
    NONSYNONYMOUS_SNV = "nonsynonymous SNV"
    SYNONYMOUS_SNV = "synonymous SNV"
    STOPGAIN = "stopgain"
    STOPLOSS = "stoploss"
    UTR_5_SNV = "5'UTR SNV"
    UTR_3_SNV = "3'UTR SNV"
    INTRONIC_SNV = "intronic SNV"

    # Indels
    FRAMESHIFT_INSERTION = "frameshift insertion"
    FRAMESHIFT_DELETION = "frameshift deletion"
    INFRAME_INSERTION = "inframe insertion"
    INFRAME_DELETION = "inframe deletion"

    # Splice variants
    SPLICING = "splicing"

    # Other
    UNKNOWN = "unknown"

    # Deprecated - for backwards compatibility with existing data
    # These will be migrated to inframe variants
    NONFRAMESHIFT_DELETION = "nonframeshift deletion"
    NONFRAMESHIFT_INSERTION = "nonframeshift insertion"

    @classmethod
    def from_string(cls, value: str | None) -> "VariantType":
        """Parse variant type from string."""
        if value is None or value.lower() in ("null", "(null)", ""):
            return cls.UNKNOWN

        value_lower = value.lower().strip()

        # Direct mapping
        for member in cls:
            if member.value.lower() == value_lower:
                return member

        # Fuzzy matching
        if "nonsynonymous" in value_lower and "snv" in value_lower:
            return cls.NONSYNONYMOUS_SNV
        if "synonymous" in value_lower and "snv" in value_lower:
            return cls.SYNONYMOUS_SNV
        # Inframe (also match old "nonframeshift" names from pipeline)
        if "inframe" in value_lower or "nonframeshift" in value_lower:
            if "insertion" in value_lower or "ins" in value_lower:
                return cls.INFRAME_INSERTION
            if "deletion" in value_lower or "del" in value_lower:
                return cls.INFRAME_DELETION
        # Frameshift
        if "frameshift" in value_lower:
            if "insertion" in value_lower or "ins" in value_lower:
                return cls.FRAMESHIFT_INSERTION
            if "deletion" in value_lower or "del" in value_lower:
                return cls.FRAMESHIFT_DELETION
        if "5'utr" in value_lower or "5utr" in value_lower:
            return cls.UTR_5_SNV
        if "3'utr" in value_lower or "3utr" in value_lower:
            return cls.UTR_3_SNV
        if "splice" in value_lower:
            return cls.SPLICING

        return cls.UNKNOWN
