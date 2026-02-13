"""Sample coverage entity - coverage statistics from pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class SampleCoverage:
    """Domain entity representing coverage statistics for a sample.

    Stores the percentage of target regions covered at various depths.
    Generated from CovWidthAtDepths.tsv file.
    """

    sample_id: UUID
    id: UUID = field(default_factory=uuid4)

    # Coverage percentages at different depths
    depth_0x: Decimal = Decimal("0")  # % covered at >0x
    depth_5x: Decimal = Decimal("0")  # % covered at >5x
    depth_30x: Decimal = Decimal("0")  # % covered at >30x
    depth_50x: Decimal = Decimal("0")  # % covered at >50x
    depth_100x: Decimal = Decimal("0")  # % covered at >100x

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, float]:
        """Convert coverage stats to dictionary."""
        return {
            "0x_depth": float(self.depth_0x),
            "5x_depth": float(self.depth_5x),
            "30x_depth": float(self.depth_30x),
            "50x_depth": float(self.depth_50x),
            "100x_depth": float(self.depth_100x),
        }
