#!/usr/bin/env python3
"""Create mock variant data for failed samples (demo purposes).

Usage:
    docker-compose exec api python scripts/create_mock_data.py
    docker-compose exec api python scripts/create_mock_data.py --status failed
    docker-compose exec api python scripts/create_mock_data.py --sample-id UUID
"""

import argparse
import asyncio
import logging
import random
import sys
from decimal import Decimal
from uuid import UUID, uuid4

# Add src to path
sys.path.insert(0, "/app")

from src.domain.enums import ACMGClassification, SampleStatus
from src.infrastructure.database import SQLAlchemyUnitOfWork, async_session_factory
from src.infrastructure.database.models import (
    SampleCoverageModel,
    SampleModel,
    SampleVariantModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Mock BRCA variants - realistic examples
MOCK_VARIANTS = [
    # BRCA1 variants
    {
        "chromosome": "17",
        "position": 43094464,
        "ref": "G",
        "alt": "A",
        "gene": "BRCA1",
        "variant_type": "missense",
        "transcript": "NM_007294.4",
        "exon_intron": "exon 10",
        "hgvs": "c.1067A>G (p.Gln356Arg)",
        "genotype": "гетерозигота",
        "acmg_classification": ACMGClassification.VUS,
        "pop_freq_gnomad": Decimal("0.0001"),
    },
    {
        "chromosome": "17",
        "position": 43091983,
        "ref": "C",
        "alt": "T",
        "gene": "BRCA1",
        "variant_type": "missense",
        "transcript": "NM_007294.4",
        "exon_intron": "exon 11",
        "hgvs": "c.1961delA (p.Lys654fs)",
        "genotype": "гетерозигота",
        "acmg_classification": ACMGClassification.PATHOGENIC,
        "pop_freq_gnomad": Decimal("0.00001"),
    },
    {
        "chromosome": "17",
        "position": 43082434,
        "ref": "A",
        "alt": "G",
        "gene": "BRCA1",
        "variant_type": "synonymous",
        "transcript": "NM_007294.4",
        "exon_intron": "exon 13",
        "hgvs": "c.4308T>C (p.Ser1436=)",
        "genotype": "гомозигота",
        "acmg_classification": ACMGClassification.BENIGN,
        "pop_freq_gnomad": Decimal("0.15"),
    },
    # BRCA2 variants
    {
        "chromosome": "13",
        "position": 32914437,
        "ref": "C",
        "alt": "T",
        "gene": "BRCA2",
        "variant_type": "missense",
        "transcript": "NM_000059.4",
        "exon_intron": "exon 11",
        "hgvs": "c.5213G>A (p.Arg1738Gln)",
        "genotype": "гетерозигота",
        "acmg_classification": ACMGClassification.LIKELY_BENIGN,
        "pop_freq_gnomad": Decimal("0.005"),
    },
    {
        "chromosome": "13",
        "position": 32913055,
        "ref": "A",
        "alt": "C",
        "gene": "BRCA2",
        "variant_type": "missense",
        "transcript": "NM_000059.4",
        "exon_intron": "exon 10",
        "hgvs": "c.1114A>C (p.Asn372His)",
        "genotype": "гетерозигота",
        "acmg_classification": ACMGClassification.VUS,
        "pop_freq_gnomad": Decimal("0.002"),
    },
    {
        "chromosome": "13",
        "position": 32929387,
        "ref": "T",
        "alt": "C",
        "gene": "BRCA2",
        "variant_type": "intronic",
        "transcript": "NM_000059.4",
        "exon_intron": "intron 14",
        "hgvs": "c.7435+10T>C",
        "genotype": "гетерозигота",
        "acmg_classification": ACMGClassification.LIKELY_BENIGN,
        "pop_freq_gnomad": Decimal("0.08"),
    },
    {
        "chromosome": "13",
        "position": 32906729,
        "ref": "AAAG",
        "alt": "A",
        "gene": "BRCA2",
        "variant_type": "frameshift",
        "transcript": "NM_000059.4",
        "exon_intron": "exon 3",
        "hgvs": "c.156_158delAAG (p.Lys53del)",
        "genotype": "гетерозигота",
        "acmg_classification": ACMGClassification.LIKELY_PATHOGENIC,
        "pop_freq_gnomad": Decimal("0.00005"),
    },
]


def generate_mock_coverage() -> dict:
    """Generate realistic mock coverage data."""
    base = random.uniform(95, 99.5)
    return {
        "depth_0x": Decimal(str(round(min(100, base + 0.5), 2))),
        "depth_5x": Decimal(str(round(base, 2))),
        "depth_30x": Decimal(str(round(base - random.uniform(0.5, 2), 2))),
        "depth_50x": Decimal(str(round(base - random.uniform(2, 5), 2))),
        "depth_100x": Decimal(str(round(base - random.uniform(5, 15), 2))),
    }


def generate_mock_variant(sample_id: UUID, variant_template: dict) -> SampleVariantModel:
    """Generate a mock variant model from template."""
    depth = random.randint(100, 500)
    allele_depth = random.randint(int(depth * 0.3), int(depth * 0.7))

    return SampleVariantModel(
        id=uuid4(),
        sample_id=sample_id,
        chromosome=variant_template["chromosome"],
        position=variant_template["position"],
        ref=variant_template["ref"],
        alt=variant_template["alt"],
        gene=variant_template["gene"],
        variant_type=variant_template["variant_type"],
        transcript=variant_template["transcript"],
        exon_intron=variant_template["exon_intron"],
        hgvs=variant_template["hgvs"],
        depth=depth,
        genotype=variant_template["genotype"],
        variant_caller="gatk,ngsep,xatlas",
        gatk_depth=depth,
        gatk_allele_depth=allele_depth,
        gatk_allele_fraction=Decimal(str(round(allele_depth / depth, 6))),
        variant_db_num=random.randint(0, 50),
        variant_db_hetero_num=random.randint(0, 30),
        variant_db_homo_num=random.randint(0, 10),
        artifact_db_num=0,
        pop_freq_gnomad=variant_template["pop_freq_gnomad"],
        acmg_classification=variant_template["acmg_classification"],
        is_variant=None,  # Not yet annotated by geneticist
        is_artifact=None,
    )


async def get_samples_by_status(uow: SQLAlchemyUnitOfWork, status: SampleStatus) -> list:
    """Get samples by status."""
    async with uow:
        from sqlalchemy import select

        stmt = select(SampleModel).where(SampleModel.status == status.value)
        result = await uow._session.execute(stmt)
        return list(result.scalars().all())


async def create_mock_data_for_sample(
    uow: SQLAlchemyUnitOfWork,
    sample: SampleModel,
    num_variants: int = 5,
) -> None:
    """Create mock variants and coverage for a sample."""
    async with uow:
        from sqlalchemy import delete, select

        # Delete existing variants for this sample
        await uow._session.execute(
            delete(SampleVariantModel).where(SampleVariantModel.sample_id == sample.id)
        )

        # Delete existing coverage
        await uow._session.execute(
            delete(SampleCoverageModel).where(SampleCoverageModel.sample_id == sample.id)
        )

        # Select random variants from templates
        selected_variants = random.sample(MOCK_VARIANTS, min(num_variants, len(MOCK_VARIANTS)))

        # Create variant models
        for variant_template in selected_variants:
            variant_model = generate_mock_variant(sample.id, variant_template)
            uow._session.add(variant_model)

        # Create coverage
        coverage_data = generate_mock_coverage()
        coverage_model = SampleCoverageModel(
            id=uuid4(),
            sample_id=sample.id,
            **coverage_data,
        )
        uow._session.add(coverage_model)

        # Update sample status to awaiting_annotation
        stmt = select(SampleModel).where(SampleModel.id == sample.id)
        result = await uow._session.execute(stmt)
        sample_model = result.scalar_one()
        sample_model.status = SampleStatus.AWAITING_ANNOTATION.value

        await uow.commit()

        logger.info(
            f"Created {len(selected_variants)} mock variants and coverage for sample "
            f"{sample.sample_code} (status: awaiting_annotation)"
        )


async def create_mock_data(
    status: str = "failed",
    sample_id: str | None = None,
    num_variants: int = 5,
):
    """Create mock data for samples."""

    # If specific sample ID provided
    if sample_id:
        logger.info(f"Creating mock data for sample {sample_id}")
        uow = SQLAlchemyUnitOfWork(async_session_factory)

        async with uow:
            from sqlalchemy import select
            stmt = select(SampleModel).where(SampleModel.id == UUID(sample_id))
            result = await uow._session.execute(stmt)
            sample = result.scalar_one_or_none()

            if not sample:
                logger.error(f"Sample {sample_id} not found")
                return

        await create_mock_data_for_sample(
            SQLAlchemyUnitOfWork(async_session_factory),
            sample,
            num_variants,
        )
        return

    # Get samples by status
    target_status = SampleStatus(status)
    samples = await get_samples_by_status(
        SQLAlchemyUnitOfWork(async_session_factory),
        target_status,
    )

    if not samples:
        logger.info(f"No samples found with status '{status}'")
        return

    logger.info(f"Found {len(samples)} samples with status '{status}'")

    # Create mock data for each sample
    for sample in samples:
        await create_mock_data_for_sample(
            SQLAlchemyUnitOfWork(async_session_factory),
            sample,
            num_variants,
        )

    logger.info(f"Completed: {len(samples)} samples updated with mock data")


def main():
    parser = argparse.ArgumentParser(description="Create mock variant data for demo")
    parser.add_argument(
        "--status",
        type=str,
        default="failed",
        help="Status of samples to process (default: failed)",
    )
    parser.add_argument(
        "--sample-id",
        type=str,
        help="Specific sample ID to process",
    )
    parser.add_argument(
        "--num-variants",
        type=int,
        default=5,
        help="Number of mock variants per sample (default: 5)",
    )

    args = parser.parse_args()

    asyncio.run(create_mock_data(
        status=args.status,
        sample_id=args.sample_id,
        num_variants=args.num_variants,
    ))


if __name__ == "__main__":
    main()
