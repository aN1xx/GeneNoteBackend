#!/usr/bin/env python3
"""Script to import germline variants from TSV file to database.

Usage:
    python scripts/import_germline_variants.py path/to/variants.tsv

This script:
1. Reads TSV file with germline variants
2. Maps variant_type and acmg_classification to enums
3. Inserts into germline_variants table (skips duplicates)
"""

import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.domain.enums import ACMGClassification, VariantType
from src.infrastructure.database import async_session_factory
from src.infrastructure.database.models.variant import VariantModel


# Extended variant type mapping for TSV values not in enum
VARIANT_TYPE_MAPPING = {
    "frameshift": VariantType.FRAMESHIFT_DELETION,  # Default to deletion
    "nonsense SNV": VariantType.STOPGAIN,
    "nonsense": VariantType.STOPGAIN,
    "start-loss": VariantType.STOPLOSS,
    "stop gain": VariantType.STOPGAIN,
    "intronic indel": VariantType.UNKNOWN,
    "Promoter SNV": VariantType.UNKNOWN,
    "inframe insertion": VariantType.INFRAME_INSERTION,
}


def parse_variant_type(value: str | None, ref: str = "", alt: str = "") -> VariantType:
    """Parse variant type with extended mapping.

    Args:
        value: Variant type string from TSV
        ref: Reference allele (to determine insertion vs deletion for frameshift)
        alt: Alternate allele
    """
    if not value:
        return VariantType.UNKNOWN

    # Handle "frameshift" - determine insertion or deletion by ref/alt length
    if value.lower() == "frameshift":
        if len(alt) > len(ref):
            return VariantType.FRAMESHIFT_INSERTION
        return VariantType.FRAMESHIFT_DELETION

    # Check extended mapping
    if value in VARIANT_TYPE_MAPPING:
        return VARIANT_TYPE_MAPPING[value]

    # Use enum's fuzzy parser
    return VariantType.from_string(value)


def parse_acmg(value: str | None) -> ACMGClassification:
    """Parse ACMG classification with fuzzy matching."""
    return ACMGClassification.from_string(value)


def parse_decimal(value: str | None) -> Decimal | None:
    """Parse decimal value."""
    if not value or value.strip() == "":
        return None
    try:
        return Decimal(str(value).strip())
    except Exception:
        return None


def parse_int(value: str | None, default: int = 0) -> int:
    """Parse integer value."""
    if not value or value.strip() == "":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def clean_chrom(chrom: str) -> str:
    """Clean chromosome (remove 'chr' prefix)."""
    return chrom.upper().replace("CHR", "").strip()


def parse_tsv_row(row: dict) -> dict:
    """Parse a single TSV row into variant data."""
    ref = row.get("ref", "").strip()
    alt = row.get("alt", "").strip()

    return {
        "id": uuid4(),
        "chromosome": clean_chrom(row.get("chrom", "")),
        "position": parse_int(row.get("pos_GRCh38")),
        "ref": ref,
        "alt": alt,
        "gene": row.get("gene", "").strip(),
        "variant_type": parse_variant_type(row.get("variant_type"), ref, alt),
        "transcript": row.get("transcript", "").strip(),
        "exon_intron": row.get("exon/intron") or None,
        "hgvs": row.get("HGVS_VariantName") or None,
        "hetero_num": parse_int(row.get("hetero_num")),
        "homo_num": parse_int(row.get("homo_num")),
        "sample_num": parse_int(row.get("sample_num")),
        "pop_freq_gnomad": parse_decimal(row.get("PopFreq_GNOMAD_v3.1.2")),
        "acmg_classification": parse_acmg(row.get("ACMG_classification")),
        "changelog": None,
    }


async def import_variants(tsv_path: Path, dry_run: bool = False) -> None:
    """Import variants from TSV file to database.

    Args:
        tsv_path: Path to TSV file
        dry_run: If True, only parse and validate, don't write to DB
    """
    if not tsv_path.exists():
        print(f"Error: File not found: {tsv_path}")
        sys.exit(1)

    # Parse TSV file
    variants_data = []
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            data = parse_tsv_row(row)
            variants_data.append(data)

    print(f"Parsed {len(variants_data)} variants from TSV")

    # Show variant type distribution
    vt_counts: dict[str, int] = {}
    acmg_counts: dict[str, int] = {}
    for v in variants_data:
        vt = v["variant_type"].value
        acmg = v["acmg_classification"].value
        vt_counts[vt] = vt_counts.get(vt, 0) + 1
        acmg_counts[acmg] = acmg_counts.get(acmg, 0) + 1

    print("\nVariant types:")
    for vt, count in sorted(vt_counts.items(), key=lambda x: -x[1]):
        print(f"  {vt}: {count}")

    print("\nACMG classifications:")
    for acmg, count in sorted(acmg_counts.items(), key=lambda x: -x[1]):
        print(f"  {acmg}: {count}")

    # Show sample variants
    print("\nFirst 5 variants:")
    for v in variants_data[:5]:
        print(f"  chr{v['chromosome']}:{v['position']} {v['ref']}>{v['alt']} "
              f"({v['gene']}) - {v['variant_type'].value} - {v['acmg_classification'].value}")

    if dry_run:
        print("\n[DRY RUN] No changes made to database")
        return

    # Insert into database
    async with async_session_factory() as session:
        inserted = 0
        skipped = 0

        for data in variants_data:
            # Check if variant already exists
            stmt = select(VariantModel).where(
                VariantModel.chromosome == data["chromosome"],
                VariantModel.position == data["position"],
                VariantModel.ref == data["ref"],
                VariantModel.alt == data["alt"],
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            # Insert new variant
            variant = VariantModel(
                id=data["id"],
                chromosome=data["chromosome"],
                position=data["position"],
                ref=data["ref"],
                alt=data["alt"],
                gene=data["gene"],
                variant_type=data["variant_type"],
                transcript=data["transcript"],
                exon_intron=data["exon_intron"],
                hgvs=data["hgvs"],
                hetero_num=data["hetero_num"],
                homo_num=data["homo_num"],
                sample_num=data["sample_num"],
                pop_freq_gnomad=data["pop_freq_gnomad"],
                acmg_classification=data["acmg_classification"],
                changelog=data["changelog"],
            )
            session.add(variant)
            inserted += 1

        await session.commit()
        print(f"\nInserted: {inserted}, Skipped (duplicates): {skipped}")


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_germline_variants.py <tsv_file> [--dry-run]")
        sys.exit(1)

    tsv_path = Path(sys.argv[1]).expanduser()
    dry_run = "--dry-run" in sys.argv

    await import_variants(tsv_path, dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
