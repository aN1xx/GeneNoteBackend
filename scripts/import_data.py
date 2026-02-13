#!/usr/bin/env python3
"""Import data from TSV files into database.

Usage:
    python -m scripts.import_data --data-dir /path/to/Pipeline_Files

This script imports:
- Patients from 2.1_Patients_DataBase.tsv
- Samples (one per patient, using request_id as sample_code)
- Variants from 2.2_GermlineVariants_DataBase.tsv
- Artifacts from 2.3_GermlineArtifacts_DataBase.tsv
"""

import argparse
import asyncio
import csv
import logging
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.entities import GermlineArtifact, GermlineVariant, Patient, Sample
from src.domain.enums import ACMGClassification, SampleStatus, Sex, VariantType
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date | None:
    """Parse date from various formats."""
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    # Try ISO format
    if "-" in date_str:
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            pass

    # Try Russian format
    formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y.%m.%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def safe_int(value: str | None, default: int = 0) -> int:
    """Safely convert value to int."""
    if not value or value.strip() == "":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_decimal(value: str | None) -> Decimal | None:
    """Safely convert value to Decimal."""
    if not value or value.strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


async def import_patients(data_dir: Path, uow: SQLAlchemyUnitOfWork) -> dict[str, Patient]:
    """Import patients from TSV file.

    Returns:
        Dictionary mapping request_id to Patient entity
    """
    file_path = data_dir / "2.1_Patients_DataBase.tsv"
    if not file_path.exists():
        logger.error(f"Patients file not found: {file_path}")
        return {}

    patients: dict[str, Patient] = {}
    imported = 0
    skipped = 0

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            request_id = row.get("request_id", "").strip()
            if not request_id:
                skipped += 1
                continue

            # Check if patient already exists
            existing = await uow.patients.get_by_request_id(request_id)
            if existing:
                patients[request_id] = existing
                skipped += 1
                continue

            # Parse patient data
            name = row.get("name", "").strip()
            if not name:
                skipped += 1
                continue

            sex_str = row.get("sex", "").strip()
            sex = Sex.from_string(sex_str)

            birth_date = parse_date(row.get("birth_date", ""))
            if not birth_date:
                logger.warning(f"Invalid birth_date for patient {name}, skipping")
                skipped += 1
                continue

            analysis_name = row.get("analysis_name", "").strip()
            analysis_date = parse_date(row.get("analysis_date", ""))

            # Create patient entity
            patient = Patient(
                id=uuid4(),
                name=name,
                sex=sex,
                birth_date=birth_date,
                request_id=request_id,
                analysis_name=analysis_name,
                analysis_date=analysis_date,
            )

            await uow.patients.save(patient)
            patients[request_id] = patient
            imported += 1

            if imported % 50 == 0:
                logger.info(f"Imported {imported} patients...")

    logger.info(f"Patients: imported={imported}, skipped={skipped}")
    return patients


async def import_samples(
    patients: dict[str, Patient],
    uow: SQLAlchemyUnitOfWork,
) -> dict[str, Sample]:
    """Create samples for each patient.

    Returns:
        Dictionary mapping request_id to Sample entity
    """
    samples: dict[str, Sample] = {}
    imported = 0
    skipped = 0

    for request_id, patient in patients.items():
        # Check if sample already exists
        existing = await uow.samples.get_by_sample_code(request_id)
        if existing:
            samples[request_id] = existing
            skipped += 1
            continue

        # Create sample using request_id as sample_code
        sample = Sample(
            id=uuid4(),
            patient_id=patient.id,
            sample_code=request_id,
            status=SampleStatus.AWAITING_ANNOTATION,  # Already processed
            collection_date=datetime.utcnow(),
        )

        await uow.samples.save(sample)
        samples[request_id] = sample
        imported += 1

    logger.info(f"Samples: imported={imported}, skipped={skipped}")
    return samples


async def import_variants(data_dir: Path, uow: SQLAlchemyUnitOfWork) -> dict[str, GermlineVariant]:
    """Import variants from TSV file.

    Returns:
        Dictionary mapping variant_name to GermlineVariant entity
    """
    file_path = data_dir / "2.2_GermlineVariants_DataBase.tsv"
    if not file_path.exists():
        logger.error(f"Variants file not found: {file_path}")
        return {}

    variants: dict[str, GermlineVariant] = {}
    imported = 0
    skipped = 0
    updated = 0

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            variant_name = row.get("VariantName", "").strip()
            if not variant_name:
                skipped += 1
                continue

            # Parse variant name: chr17-43063912-A-G
            parts = variant_name.replace("chr", "").split("-")
            if len(parts) < 4:
                logger.warning(f"Invalid variant name: {variant_name}")
                skipped += 1
                continue

            chrom = parts[0]
            try:
                position = int(parts[1])
            except ValueError:
                logger.warning(f"Invalid position in variant: {variant_name}")
                skipped += 1
                continue
            ref = parts[2]
            alt = parts[3].split("-")[0]  # Handle chr13-32316435-G-A-het

            # Check if variant already exists
            existing = await uow.variants.get_by_coordinates(chrom, position, ref, alt)
            if existing:
                variants[variant_name] = existing
                # Update statistics
                existing.hetero_num = safe_int(row.get("hetero_num"))
                existing.homo_num = safe_int(row.get("homo_num"))
                existing.sample_num = safe_int(row.get("sample_num"))
                await uow.variants.save(existing)
                updated += 1
                continue

            # Parse ACMG classification
            acmg_str = row.get("ACMG_classification", "").strip()
            acmg = ACMGClassification.from_string(acmg_str)

            # Parse variant type
            variant_type_str = row.get("variant_type", "").strip()
            variant_type = VariantType.from_string(variant_type_str)

            # Create variant entity
            variant = GermlineVariant(
                id=uuid4(),
                chromosome=chrom,
                position=position,
                ref=ref,
                alt=alt,
                gene=row.get("gene", "").strip().upper() or "UNKNOWN",
                variant_type=variant_type,
                transcript=row.get("transcript", "").strip(),
                exon_intron=row.get("exon/intron", "").strip() or None,
                hgvs=row.get("HGVS_VariantName", "").strip() or None,
                hetero_num=safe_int(row.get("hetero_num")),
                homo_num=safe_int(row.get("homo_num")),
                sample_num=safe_int(row.get("sample_num")),
                pop_freq_gnomad=safe_decimal(row.get("PopFreq_GNOMAD_v3.1.2")),
                acmg_classification=acmg,
            )

            await uow.variants.save(variant)
            variants[variant_name] = variant
            imported += 1

            if imported % 20 == 0:
                logger.info(f"Imported {imported} variants...")

    logger.info(f"Variants: imported={imported}, updated={updated}, skipped={skipped}")
    return variants


async def import_artifacts(data_dir: Path, uow: SQLAlchemyUnitOfWork) -> int:
    """Import artifacts from TSV file.

    Returns:
        Number of imported artifacts
    """
    file_path = data_dir / "2.3_GermlineArtifacts_DataBase.tsv"
    if not file_path.exists():
        logger.error(f"Artifacts file not found: {file_path}")
        return 0

    imported = 0
    skipped = 0

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            artifact_name = row.get("ArtifactName", "").strip()
            if not artifact_name:
                skipped += 1
                continue

            # Parse artifact name: chr17-43063912-A-G
            parts = artifact_name.replace("chr", "").split("-")
            if len(parts) < 4:
                logger.warning(f"Invalid artifact name: {artifact_name}")
                skipped += 1
                continue

            chrom = parts[0]
            try:
                position = int(parts[1])
            except ValueError:
                logger.warning(f"Invalid position in artifact: {artifact_name}")
                skipped += 1
                continue
            ref = parts[2]
            alt = parts[3]

            # Check if artifact already exists
            existing = await uow.artifacts.get_by_coordinates(chrom, position, ref, alt)
            if existing:
                # Update statistics
                existing.occurrence_num = safe_int(row.get("occurrence_num"))
                existing.sample_num = safe_int(row.get("sample_num"))
                await uow.artifacts.save(existing)
                skipped += 1
                continue

            # Create artifact entity
            artifact = GermlineArtifact(
                id=uuid4(),
                chromosome=chrom,
                position=position,
                ref=ref,
                alt=alt,
                occurrence_num=safe_int(row.get("occurrence_num")),
                sample_num=safe_int(row.get("sample_num")),
            )

            await uow.artifacts.save(artifact)
            imported += 1

    logger.info(f"Artifacts: imported={imported}, skipped={skipped}")
    return imported


async def link_patient_variants(
    data_dir: Path,
    patients: dict[str, Patient],
    variants: dict[str, GermlineVariant],
    uow: SQLAlchemyUnitOfWork,
) -> int:
    """Link patients to their variants based on 2.1_Patients_DataBase.tsv.

    Returns:
        Number of links created
    """
    file_path = data_dir / "2.1_Patients_DataBase.tsv"
    if not file_path.exists():
        return 0

    links_created = 0

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            request_id = row.get("request_id", "").strip()
            variants_str = row.get("variants", "").strip()

            if not request_id or not variants_str:
                continue

            patient = patients.get(request_id)
            if not patient:
                continue

            # Parse variants list: chr13-32316435-G-A-het,chr13-32337751-A-G-het,...
            variant_names = [v.strip() for v in variants_str.split(",") if v.strip()]

            for vname in variant_names:
                # Remove zygosity suffix if present
                base_name = "-".join(vname.split("-")[:4])
                variant = variants.get(base_name)
                if variant and variant.id not in patient.variant_ids:
                    patient.add_variant(variant.id)
                    links_created += 1

            await uow.patients.save(patient)

    logger.info(f"Patient-variant links created: {links_created}")
    return links_created


async def main(data_dir: Path) -> None:
    """Main import function."""
    logger.info(f"Starting data import from {data_dir}")

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)

    uow = SQLAlchemyUnitOfWork(async_session_factory)

    async with uow:
        # Import patients
        logger.info("Importing patients...")
        patients = await import_patients(data_dir, uow)

        # Create samples
        logger.info("Creating samples...")
        await import_samples(patients, uow)

        # Import variants
        logger.info("Importing variants...")
        variants = await import_variants(data_dir, uow)

        # Import artifacts
        logger.info("Importing artifacts...")
        await import_artifacts(data_dir, uow)

        # Link patients to variants
        logger.info("Linking patients to variants...")
        await link_patient_variants(data_dir, patients, variants, uow)

        # Commit all changes
        await uow.commit()

    logger.info("Import completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import data from TSV files")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data/pipeline_files"),
        help="Path to Pipeline_Files directory",
    )
    args = parser.parse_args()

    asyncio.run(main(args.data_dir))
