"""Tests for domain enums."""

from src.domain.enums import (
    ACMGClassification,
    PipelineStatus,
    PipelineType,
    SampleStatus,
    Sex,
    UserRole,
    VariantType,
)


class TestSex:
    """Tests for Sex enum."""

    def test_from_string_male(self) -> None:
        """Test parsing male sex."""
        assert Sex.from_string("М") == Sex.MALE
        assert Sex.from_string("м") == Sex.MALE
        assert Sex.from_string("male") == Sex.MALE
        assert Sex.from_string("MALE") == Sex.MALE
        assert Sex.from_string("m") == Sex.MALE

    def test_from_string_female(self) -> None:
        """Test parsing female sex."""
        assert Sex.from_string("Ж") == Sex.FEMALE
        assert Sex.from_string("ж") == Sex.FEMALE
        assert Sex.from_string("female") == Sex.FEMALE
        assert Sex.from_string("FEMALE") == Sex.FEMALE
        assert Sex.from_string("f") == Sex.FEMALE

    def test_from_string_unknown(self) -> None:
        """Test parsing unknown sex."""
        assert Sex.from_string("unknown") == Sex.UNKNOWN
        assert Sex.from_string("") == Sex.UNKNOWN
        assert Sex.from_string("xyz") == Sex.UNKNOWN


class TestVariantType:
    """Tests for VariantType enum."""

    def test_from_string_snv(self) -> None:
        """Test parsing SNV."""
        assert VariantType.from_string("SNV") == VariantType.SNV
        assert VariantType.from_string("snv") == VariantType.SNV

    def test_from_string_nonsynonymous_snv(self) -> None:
        """Test parsing nonsynonymous SNV."""
        assert VariantType.from_string("nonsynonymous SNV") == VariantType.NONSYNONYMOUS_SNV

    def test_from_string_frameshift_insertion(self) -> None:
        """Test parsing frameshift insertion."""
        assert VariantType.from_string("frameshift insertion") == VariantType.FRAMESHIFT_INSERTION

    def test_from_string_frameshift_deletion(self) -> None:
        """Test parsing frameshift deletion."""
        assert VariantType.from_string("frameshift deletion") == VariantType.FRAMESHIFT_DELETION

    def test_from_string_unknown(self) -> None:
        """Test parsing unknown type."""
        assert VariantType.from_string("xyz") == VariantType.UNKNOWN


class TestACMGClassification:
    """Tests for ACMGClassification enum."""

    def test_from_string_pathogenic(self) -> None:
        """Test parsing pathogenic."""
        assert ACMGClassification.from_string("pathogenic") == ACMGClassification.PATHOGENIC
        assert ACMGClassification.from_string("PATHOGENIC") == ACMGClassification.PATHOGENIC
        assert ACMGClassification.from_string("Патогенный") == ACMGClassification.PATHOGENIC

    def test_from_string_benign(self) -> None:
        """Test parsing benign."""
        assert ACMGClassification.from_string("benign") == ACMGClassification.BENIGN
        assert ACMGClassification.from_string("Доброкачественный") == ACMGClassification.BENIGN

    def test_from_string_vus(self) -> None:
        """Test parsing VUS."""
        assert ACMGClassification.from_string("vus") == ACMGClassification.VUS
        assert ACMGClassification.from_string("Вариант неясного значения") == ACMGClassification.VUS

    def test_from_string_not_classified(self) -> None:
        """Test parsing not classified."""
        assert ACMGClassification.from_string("") == ACMGClassification.NOT_CLASSIFIED
        assert ACMGClassification.from_string("unknown") == ACMGClassification.NOT_CLASSIFIED


class TestUserRole:
    """Tests for UserRole enum."""

    def test_role_values(self) -> None:
        """Test role values."""
        assert UserRole.LABORANT.value == "laborant"
        assert UserRole.GENETICIST.value == "geneticist"
        assert UserRole.ADMIN.value == "admin"


class TestSampleStatus:
    """Tests for SampleStatus enum."""

    def test_status_values(self) -> None:
        """Test status values."""
        assert SampleStatus.UPLOADED.value == "uploaded"
        assert SampleStatus.PROCESSING.value == "processing"
        assert SampleStatus.AWAITING_ANNOTATION.value == "awaiting_annotation"
        assert SampleStatus.ANNOTATED.value == "annotated"
        assert SampleStatus.REPORT_GENERATED.value == "report_generated"
        assert SampleStatus.FAILED.value == "failed"


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_status_values(self) -> None:
        """Test pipeline status values."""
        assert PipelineStatus.QUEUED.value == "queued"
        assert PipelineStatus.RUNNING.value == "running"
        assert PipelineStatus.COMPLETED.value == "completed"
        assert PipelineStatus.FAILED.value == "failed"


class TestPipelineType:
    """Tests for PipelineType enum."""

    def test_type_values(self) -> None:
        """Test pipeline type values."""
        assert PipelineType.VARIANT_CALLING.value == "variant_calling"
        assert PipelineType.REPORT_GENERATION.value == "report_generation"
