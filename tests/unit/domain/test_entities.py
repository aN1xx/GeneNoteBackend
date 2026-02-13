"""Tests for domain entities."""

from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities import GermlineVariant, Patient, Sample, User
from src.domain.enums import (
    ACMGClassification,
    SampleStatus,
    Sex,
    UserRole,
    VariantType,
)


class TestUser:
    """Tests for User entity."""

    def test_create_user(self) -> None:
        """Test user creation."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.LABORANT,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.LABORANT
        assert user.is_active is True

    def test_user_deactivate(self) -> None:
        """Test user deactivation."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.LABORANT,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        user.deactivate()
        assert user.is_active is False

    def test_user_activate(self) -> None:
        """Test user activation."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.LABORANT,
            is_active=False,
            created_at=datetime.now(UTC),
        )
        user.activate()
        assert user.is_active is True


class TestPatient:
    """Tests for Patient entity."""

    def test_create_patient(self) -> None:
        """Test patient creation."""
        patient = Patient(
            id=uuid4(),
            name="Test Patient",
            sex=Sex.MALE,
            birth_date=datetime(1990, 1, 15).date(),
            request_id="REQ-001",
            analysis_name="WES Analysis",
            created_at=datetime.now(UTC),
        )
        assert patient.name == "Test Patient"
        assert patient.sex == Sex.MALE
        assert patient.request_id == "REQ-001"

    def test_patient_format_birth_date(self) -> None:
        """Test birth date formatting."""
        patient = Patient(
            id=uuid4(),
            name="Test Patient",
            sex=Sex.FEMALE,
            birth_date=datetime(1990, 1, 15).date(),
            request_id="REQ-001",
            analysis_name="WES",
            created_at=datetime.now(UTC),
        )
        formatted = patient.format_birth_date()
        assert "1990" in formatted or "15" in formatted


class TestSample:
    """Tests for Sample entity."""

    def test_create_sample(self) -> None:
        """Test sample creation."""
        patient_id = uuid4()
        sample = Sample(
            id=uuid4(),
            patient_id=patient_id,
            sample_code="SAMPLE-001",
            status=SampleStatus.UPLOADED,
            created_at=datetime.now(UTC),
        )
        assert sample.sample_code == "SAMPLE-001"
        assert sample.status == SampleStatus.UPLOADED
        assert sample.patient_id == patient_id

    def test_sample_status_transitions(self) -> None:
        """Test sample status transitions."""
        sample = Sample(
            id=uuid4(),
            patient_id=uuid4(),
            sample_code="SAMPLE-001",
            status=SampleStatus.UPLOADED,
            created_at=datetime.now(UTC),
        )

        sample.mark_processing()
        assert sample.status == SampleStatus.PROCESSING

        sample.mark_awaiting_annotation()
        assert sample.status == SampleStatus.AWAITING_ANNOTATION


class TestGermlineVariant:
    """Tests for GermlineVariant entity."""

    def test_create_variant(self) -> None:
        """Test variant creation."""
        variant = GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            hetero_num=5,
            homo_num=2,
            sample_num=7,
        )
        assert variant.chromosome == "1"
        assert variant.position == 12345
        assert variant.gene == "BRCA1"

    def test_variant_name_property(self) -> None:
        """Test variant_name property."""
        variant = GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            hetero_num=0,
            homo_num=0,
            sample_num=0,
        )
        assert "1" in variant.variant_name
        assert "12345" in variant.variant_name

    def test_variant_update_statistics(self) -> None:
        """Test variant statistics update."""
        variant = GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            hetero_num=5,
            homo_num=2,
            sample_num=7,
        )

        # Update with heterozygous
        variant.update_statistics(is_heterozygous=True)
        assert variant.hetero_num == 6
        assert variant.sample_num == 8

        # Update with homozygous
        variant.update_statistics(is_heterozygous=False)
        assert variant.homo_num == 3
        assert variant.sample_num == 9

    def test_variant_annotate(self) -> None:
        """Test variant annotation."""
        variant = GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            hetero_num=0,
            homo_num=0,
            sample_num=0,
        )

        variant.annotate(
            acmg_classification=ACMGClassification.PATHOGENIC,
            variant_type=VariantType.NONSYNONYMOUS_SNV,
        )

        assert variant.acmg_classification == ACMGClassification.PATHOGENIC
        assert variant.variant_type == VariantType.NONSYNONYMOUS_SNV

    def test_variant_update_acmg_with_changelog(self) -> None:
        """Test ACMG update with changelog tracking."""
        variant = GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            acmg_classification=ACMGClassification.VUS,
        )

        # First change: VUS -> PATHOGENIC
        variant.update_acmg_with_changelog(ACMGClassification.PATHOGENIC)

        assert variant.acmg_classification == ACMGClassification.PATHOGENIC
        assert variant.changelog is not None
        assert '"Вариант неясного значения"' in variant.changelog
        assert '"Патогенный"' in variant.changelog
        assert "значение ACMG было изменено" in variant.changelog

        # Second change: PATHOGENIC -> BENIGN
        variant.update_acmg_with_changelog(ACMGClassification.BENIGN)

        assert variant.acmg_classification == ACMGClassification.BENIGN
        # Both changes should be in changelog
        assert variant.changelog.count("значение ACMG было изменено") == 2
        assert '"Доброкачественный"' in variant.changelog

    def test_variant_update_acmg_same_value_no_changelog(self) -> None:
        """Test that setting same ACMG value doesn't add changelog entry."""
        variant = GermlineVariant(
            id=uuid4(),
            chromosome="1",
            position=12345,
            ref="A",
            alt="G",
            gene="BRCA1",
            variant_type=VariantType.SNV,
            transcript="NM_007294.4",
            acmg_classification=ACMGClassification.PATHOGENIC,
        )

        # Try to set same value
        variant.update_acmg_with_changelog(ACMGClassification.PATHOGENIC)

        # No changelog should be created
        assert variant.changelog is None
        assert variant.acmg_classification == ACMGClassification.PATHOGENIC
