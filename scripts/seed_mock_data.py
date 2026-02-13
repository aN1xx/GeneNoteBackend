"""Seed mock data for testing endpoints."""

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.domain.enums import (
    ACMGClassification,
    PipelineStatus,
    PipelineType,
    SampleStatus,
    Sex,
    UserRole,
)
from src.infrastructure.database import async_session_factory
from src.infrastructure.database.models import (
    PatientModel,
    PipelineRunModel,
    SampleCoverageModel,
    SampleModel,
    SampleVariantModel,
    UserModel,
)
from src.infrastructure.security import PasswordService


async def seed_users(session) -> dict[str, UserModel]:
    """Create test users."""
    password_service = PasswordService()
    hashed_password = password_service.hash("Test123!")

    users = {
        "laborant": UserModel(
            id=uuid4(),
            email="laborant@genenote.test",
            hashed_password=hashed_password,
            role=UserRole.LABORANT,
            is_active=True,
        ),
        "geneticist": UserModel(
            id=uuid4(),
            email="geneticist@genenote.test",
            hashed_password=hashed_password,
            role=UserRole.GENETICIST,
            is_active=True,
        ),
        "admin": UserModel(
            id=uuid4(),
            email="admin@genenote.test",
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
        ),
    }

    for user in users.values():
        session.add(user)

    print(f"Created {len(users)} users")
    return users


async def seed_patients(session) -> list[PatientModel]:
    """Create test patients."""
    patients_data = [
        {
            "name": "Иванов Иван Иванович",
            "sex": Sex.MALE,
            "birth_date": date(1985, 3, 15),
            "request_id": "REQ-2024-001",
            "analysis_name": "BRCA1/BRCA2 панель",
        },
        {
            "name": "Петрова Мария Сергеевна",
            "sex": Sex.FEMALE,
            "birth_date": date(1990, 7, 22),
            "request_id": "REQ-2024-002",
            "analysis_name": "BRCA1/BRCA2 панель",
        },
        {
            "name": "Сидоров Алексей Петрович",
            "sex": Sex.MALE,
            "birth_date": date(1978, 11, 8),
            "request_id": "REQ-2024-003",
            "analysis_name": "Онкопанель расширенная",
        },
        {
            "name": "Козлова Анна Викторовна",
            "sex": Sex.FEMALE,
            "birth_date": date(1995, 1, 30),
            "request_id": "REQ-2024-004",
            "analysis_name": "BRCA1/BRCA2 панель",
        },
        {
            "name": "Новиков Дмитрий Александрович",
            "sex": Sex.MALE,
            "birth_date": date(1982, 5, 12),
            "request_id": "REQ-2024-005",
            "analysis_name": "Наследственный рак",
        },
    ]

    patients = []
    for data in patients_data:
        patient = PatientModel(
            id=uuid4(),
            name=data["name"],
            sex=data["sex"],
            birth_date=data["birth_date"],
            request_id=data["request_id"],
            analysis_name=data["analysis_name"],
            analysis_date=date.today() - timedelta(days=len(patients)),
        )
        session.add(patient)
        patients.append(patient)

    print(f"Created {len(patients)} patients")
    return patients


async def seed_samples(
    session, patients: list[PatientModel], users: dict[str, UserModel]
) -> list[SampleModel]:
    """Create test samples with different statuses."""
    samples = []
    statuses = [
        SampleStatus.UPLOADED,
        SampleStatus.PROCESSING,
        SampleStatus.AWAITING_ANNOTATION,
        SampleStatus.ANNOTATED,
        SampleStatus.REPORT_GENERATED,
    ]

    for i, patient in enumerate(patients):
        # Each patient gets 1-2 samples
        num_samples = 1 if i % 2 == 0 else 2

        for j in range(num_samples):
            sample_code = f"{10000000 + i * 10 + j}.{j + 1}"
            status = statuses[i % len(statuses)]

            sample = SampleModel(
                id=uuid4(),
                patient_id=patient.id,
                sample_code=sample_code,
                status=status,
                collection_date=datetime.now() - timedelta(days=i * 2),
                fastq_r1_path=f"/data/files/{sample_code}_R1.fastq.gz",
                fastq_r2_path=f"/data/files/{sample_code}_R2.fastq.gz",
                uploaded_at=datetime.now() - timedelta(days=i * 2),
                uploaded_by_id=users["laborant"].id,
            )

            # Add processing timestamps based on status
            if status in [
                SampleStatus.AWAITING_ANNOTATION,
                SampleStatus.ANNOTATED,
                SampleStatus.REPORT_GENERATED,
            ]:
                sample.processed_at = datetime.now() - timedelta(days=i)

            if status in [SampleStatus.ANNOTATED, SampleStatus.REPORT_GENERATED]:
                sample.annotated_at = datetime.now() - timedelta(hours=i * 6)
                sample.annotated_by_id = users["geneticist"].id
                sample.coverage_quality_passed = True

            if status == SampleStatus.REPORT_GENERATED:
                sample.report_path = f"/data/reports/{sample_code}_report.pdf"

            session.add(sample)
            samples.append(sample)

    print(f"Created {len(samples)} samples")
    return samples


async def seed_sample_variants(session, samples: list[SampleModel]) -> None:
    """Create test variants for samples."""
    # Sample variants for samples that are awaiting annotation or further
    variant_samples = [
        s
        for s in samples
        if s.status
        in [
            SampleStatus.AWAITING_ANNOTATION,
            SampleStatus.ANNOTATED,
            SampleStatus.REPORT_GENERATED,
        ]
    ]

    variant_templates = [
        {
            "chromosome": "17",
            "position": 43094464,
            "ref": "G",
            "alt": "A",
            "gene": "BRCA1",
            "variant_type": "missense",
            "transcript": "NM_007294.4",
            "exon_intron": "exon 10",
            "hgvs": "c.1961A>G",
            "depth": 150,
            "genotype": "гетерозигота",
            "variant_caller": "gatk,ngsep",
            "acmg": ACMGClassification.LIKELY_PATHOGENIC,
        },
        {
            "chromosome": "13",
            "position": 32936732,
            "ref": "C",
            "alt": "T",
            "gene": "BRCA2",
            "variant_type": "nonsense",
            "transcript": "NM_000059.4",
            "exon_intron": "exon 11",
            "hgvs": "c.6275C>T",
            "depth": 200,
            "genotype": "гетерозигота",
            "variant_caller": "gatk,ngsep,xatlas",
            "acmg": ACMGClassification.PATHOGENIC,
        },
        {
            "chromosome": "17",
            "position": 43076614,
            "ref": "T",
            "alt": "C",
            "gene": "BRCA1",
            "variant_type": "synonymous",
            "transcript": "NM_007294.4",
            "exon_intron": "exon 16",
            "hgvs": "c.4837T>C",
            "depth": 180,
            "genotype": "гомозигота",
            "variant_caller": "gatk",
            "acmg": ACMGClassification.BENIGN,
        },
        {
            "chromosome": "13",
            "position": 32914437,
            "ref": "A",
            "alt": "G",
            "gene": "BRCA2",
            "variant_type": "intronic",
            "transcript": "NM_000059.4",
            "exon_intron": "intron 5",
            "hgvs": "c.476+15A>G",
            "depth": 120,
            "genotype": "гетерозигота",
            "variant_caller": "ngsep",
            "acmg": ACMGClassification.VUS,
        },
        {
            "chromosome": "17",
            "position": 43091983,
            "ref": "TAGA",
            "alt": "T",
            "gene": "BRCA1",
            "variant_type": "frameshift",
            "transcript": "NM_007294.4",
            "exon_intron": "exon 11",
            "hgvs": "c.2285_2287del",
            "depth": 95,
            "genotype": "гетерозигота",
            "variant_caller": "gatk,xatlas",
            "acmg": ACMGClassification.PATHOGENIC,
        },
    ]

    total_variants = 0
    for sample in variant_samples:
        # Add 3-5 variants per sample
        num_variants = 3 + (hash(str(sample.id)) % 3)

        for i in range(num_variants):
            template = variant_templates[i % len(variant_templates)]

            # Determine if annotated based on sample status
            is_annotated = sample.status in [
                SampleStatus.ANNOTATED,
                SampleStatus.REPORT_GENERATED,
            ]

            variant = SampleVariantModel(
                id=uuid4(),
                sample_id=sample.id,
                chromosome=template["chromosome"],
                position=template["position"] + i * 100,  # Slightly different positions
                ref=template["ref"],
                alt=template["alt"],
                gene=template["gene"],
                variant_type=template["variant_type"],
                transcript=template["transcript"],
                exon_intron=template["exon_intron"],
                hgvs=template["hgvs"],
                depth=template["depth"],
                genotype=template["genotype"],
                variant_caller=template["variant_caller"],
                gatk_depth=template["depth"] - 10,
                gatk_allele_depth=template["depth"] // 2,
                gatk_allele_fraction=Decimal("0.48"),
                variant_db_num=i + 1,
                variant_db_hetero_num=i,
                variant_db_homo_num=0,
                artifact_db_num=0,
                pop_freq_gnomad=Decimal("0.001") if i % 2 == 0 else None,
                acmg_classification=template["acmg"] if is_annotated else None,
                is_variant=True if is_annotated else None,
                is_artifact=False if is_annotated else None,
            )
            session.add(variant)
            total_variants += 1

    print(f"Created {total_variants} sample variants")


async def seed_sample_coverage(session, samples: list[SampleModel]) -> None:
    """Create test coverage data for processed samples."""
    processed_samples = [
        s
        for s in samples
        if s.status
        in [
            SampleStatus.AWAITING_ANNOTATION,
            SampleStatus.ANNOTATED,
            SampleStatus.REPORT_GENERATED,
        ]
    ]

    for sample in processed_samples:
        coverage = SampleCoverageModel(
            id=uuid4(),
            sample_id=sample.id,
            depth_0x=Decimal("99.8"),
            depth_5x=Decimal("99.2"),
            depth_30x=Decimal("97.5"),
            depth_50x=Decimal("95.1"),
            depth_100x=Decimal("88.3"),
        )
        session.add(coverage)

    print(f"Created {len(processed_samples)} coverage records")


async def seed_pipeline_runs(session, samples: list[SampleModel]) -> None:
    """Create test pipeline runs for samples."""
    pipeline_runs = []

    for sample in samples:
        # Variant calling pipeline for all samples
        if sample.status == SampleStatus.UPLOADED:
            # Pending pipeline
            run = PipelineRunModel(
                id=uuid4(),
                sample_id=sample.id,
                pipeline_type=PipelineType.VARIANT_CALLING,
                status=PipelineStatus.PENDING,
            )
        elif sample.status == SampleStatus.PROCESSING:
            # Running pipeline
            run = PipelineRunModel(
                id=uuid4(),
                sample_id=sample.id,
                pipeline_type=PipelineType.VARIANT_CALLING,
                status=PipelineStatus.RUNNING,
                started_at=datetime.now() - timedelta(minutes=30),
                progress_percent=45,
            )
        elif sample.status in [
            SampleStatus.AWAITING_ANNOTATION,
            SampleStatus.ANNOTATED,
            SampleStatus.REPORT_GENERATED,
        ]:
            # Completed variant calling
            run = PipelineRunModel(
                id=uuid4(),
                sample_id=sample.id,
                pipeline_type=PipelineType.VARIANT_CALLING,
                status=PipelineStatus.COMPLETED,
                started_at=datetime.now() - timedelta(hours=2),
                completed_at=datetime.now() - timedelta(hours=1),
                progress_percent=100,
                output_path=f"/app/pipeline/results/{sample.sample_code}/{sample.sample_code}_variants_raw.tsv",
            )
        else:
            # Failed pipeline
            run = PipelineRunModel(
                id=uuid4(),
                sample_id=sample.id,
                pipeline_type=PipelineType.VARIANT_CALLING,
                status=PipelineStatus.FAILED,
                started_at=datetime.now() - timedelta(hours=1),
                completed_at=datetime.now() - timedelta(minutes=30),
                error_message="Pipeline failed: out of memory",
            )

        session.add(run)
        pipeline_runs.append(run)

        # Report generation for annotated samples
        if sample.status == SampleStatus.REPORT_GENERATED:
            report_run = PipelineRunModel(
                id=uuid4(),
                sample_id=sample.id,
                pipeline_type=PipelineType.REPORT_GENERATION,
                status=PipelineStatus.COMPLETED,
                started_at=datetime.now() - timedelta(minutes=45),
                completed_at=datetime.now() - timedelta(minutes=30),
                progress_percent=100,
                output_path=f"/data/reports/{sample.sample_code}_report.pdf",
            )
            session.add(report_run)
            pipeline_runs.append(report_run)

    print(f"Created {len(pipeline_runs)} pipeline runs")


async def main(force: bool = False):
    """Main function to seed all mock data."""
    print("=" * 50)
    print("Seeding mock data for GeneNote Backend")
    print("=" * 50)
    print(f"Database: {settings.database_url.split('@')[-1]}")
    print()

    async with async_session_factory() as session:
        try:
            # Check if data already exists
            from sqlalchemy import delete, select

            existing_users = await session.execute(
                select(UserModel).where(UserModel.email.like("%@genenote.test"))
            )
            existing_patients = await session.execute(
                select(PatientModel).where(PatientModel.request_id.like("REQ-2024-00%"))
            )
            has_existing_data = (
                existing_users.scalars().first() is not None
                or existing_patients.scalars().first() is not None
            )

            if has_existing_data and not force:
                print("Mock data already exists. Use --force to recreate.")
                print()
                print("Test credentials:")
                print("  Email: laborant@genenote.test | Password: Test123!")
                print("  Email: geneticist@genenote.test | Password: Test123!")
                print("  Email: admin@genenote.test | Password: Test123!")
                return

            # Always delete existing mock data when --force (in correct order due to foreign keys)
            if force:
                print("Deleting existing mock data...")

                # Get sample IDs first for related deletes
                existing_samples = await session.execute(
                    select(SampleModel.id).where(
                        SampleModel.sample_code.like("1000000%")
                    )
                )
                sample_ids = [row[0] for row in existing_samples.fetchall()]

                if sample_ids:
                    # Delete pipeline runs
                    await session.execute(
                        delete(PipelineRunModel).where(
                            PipelineRunModel.sample_id.in_(sample_ids)
                        )
                    )
                    # Delete sample variants
                    await session.execute(
                        delete(SampleVariantModel).where(
                            SampleVariantModel.sample_id.in_(sample_ids)
                        )
                    )
                    # Delete sample coverages
                    await session.execute(
                        delete(SampleCoverageModel).where(
                            SampleCoverageModel.sample_id.in_(sample_ids)
                        )
                    )
                    # Delete samples
                    await session.execute(
                        delete(SampleModel).where(SampleModel.id.in_(sample_ids))
                    )

                # Delete patients
                await session.execute(
                    delete(PatientModel).where(
                        PatientModel.request_id.like("REQ-2024-00%")
                    )
                )

                # Delete users
                await session.execute(
                    delete(UserModel).where(UserModel.email.like("%@genenote.test"))
                )

                await session.commit()
                print("Deleted existing mock data.")

            # Seed data
            users = await seed_users(session)
            patients = await seed_patients(session)
            samples = await seed_samples(session, patients, users)
            await seed_sample_variants(session, samples)
            await seed_sample_coverage(session, samples)
            await seed_pipeline_runs(session, samples)

            await session.commit()
            print()
            print("=" * 50)
            print("Mock data seeded successfully!")
            print("=" * 50)
            print()
            print("Test credentials:")
            print("  Email: laborant@genenote.test | Password: Test123!")
            print("  Email: geneticist@genenote.test | Password: Test123!")
            print("  Email: admin@genenote.test | Password: Test123!")
            print()
            print("Sample statuses:")
            for sample in samples:
                print(f"  {sample.sample_code}: {sample.status}")

        except Exception as e:
            await session.rollback()
            print(f"Error seeding data: {e}")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed mock data for testing")
    parser.add_argument("--force", action="store_true", help="Force recreate mock data")
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
