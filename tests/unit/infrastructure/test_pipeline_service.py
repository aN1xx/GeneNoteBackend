"""Tests for PipelineService - integrates Snakemake pipeline with backend."""

import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.domain.entities import Sample
from src.domain.enums import SampleStatus
from src.infrastructure.pipeline.pipeline_service import (
    PipelineConfig,
    PipelineResult,
    PipelineService,
)


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_from_settings(self) -> None:
        """Test creating config from application settings."""
        with patch("src.infrastructure.pipeline.pipeline_service.settings") as mock_settings:
            mock_settings.pipeline_path = Path("/test/pipeline")

            config = PipelineConfig.from_settings()

            assert config.pipeline_base_path == Path("/test/pipeline")
            assert config.pipeline_script == Path("/test/pipeline/src/pipeline.py")
            assert config.pipeline_config == Path("/test/pipeline/src/pipeline_config.yaml")
            assert config.results_path == Path("/test/pipeline/results")
            assert config.databases_path == Path("/test/pipeline/data_bases")
            assert config.variants_db == Path(
                "/test/pipeline/data_bases/GermlineVariants_DataBase.tsv"
            )
            assert config.artifacts_db == Path(
                "/test/pipeline/data_bases/GermlineArtifacts_DataBase.tsv"
            )
            assert config.genome_fasta == Path(
                "/test/pipeline/references/GRCh38/fasta_and_index/GRCh38.fa"
            )
            assert config.ngsep_jar == Path("/opt/ngsep/NGSEPcore_5.0.0.jar")
            assert config.vep_cache_dir == Path("/app/vep_cache")

    def test_manual_config(self) -> None:
        """Test creating config manually."""
        config = PipelineConfig(
            pipeline_base_path=Path("/custom/path"),
            pipeline_script=Path("/custom/path/pipeline.py"),
            pipeline_config=Path("/custom/path/config.yaml"),
            results_path=Path("/custom/results"),
            databases_path=Path("/custom/dbs"),
            variants_db=Path("/custom/variants.tsv"),
            artifacts_db=Path("/custom/artifacts.tsv"),
            genome_fasta=Path("/custom/genome.fa"),
            ngsep_jar=Path("/custom/ngsep.jar"),
            vep_cache_dir=Path("/custom/vep_cache"),
        )

        assert config.pipeline_base_path == Path("/custom/path")
        assert config.results_path == Path("/custom/results")
        assert config.vep_cache_dir == Path("/custom/vep_cache")


class TestPipelineService:
    """Tests for PipelineService."""

    @pytest.fixture
    def temp_pipeline_dir(self, tmp_path: Path) -> Path:
        """Create temporary pipeline directory structure."""
        # Create expected directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "results").mkdir()
        (tmp_path / "data_bases").mkdir()
        (tmp_path / "references" / "GRCh38" / "fasta_and_index").mkdir(parents=True)

        # Create placeholder files
        (tmp_path / "src" / "pipeline.py").touch()
        (tmp_path / "src" / "pipeline_config.yaml").touch()
        (tmp_path / "data_bases" / "GermlineVariants_DataBase.tsv").touch()
        (tmp_path / "data_bases" / "GermlineArtifacts_DataBase.tsv").touch()
        (tmp_path / "references" / "GRCh38" / "fasta_and_index" / "GRCh38.fa").touch()

        return tmp_path

    @pytest.fixture
    def config(self, temp_pipeline_dir: Path) -> PipelineConfig:
        """Create test pipeline config."""
        return PipelineConfig(
            pipeline_base_path=temp_pipeline_dir,
            pipeline_script=temp_pipeline_dir / "src" / "pipeline.py",
            pipeline_config=temp_pipeline_dir / "src" / "pipeline_config.yaml",
            results_path=temp_pipeline_dir / "results",
            databases_path=temp_pipeline_dir / "data_bases",
            variants_db=temp_pipeline_dir / "data_bases" / "GermlineVariants_DataBase.tsv",
            artifacts_db=temp_pipeline_dir / "data_bases" / "GermlineArtifacts_DataBase.tsv",
            genome_fasta=(
                temp_pipeline_dir / "references" / "GRCh38" / "fasta_and_index" / "GRCh38.fa"
            ),
            ngsep_jar=Path("/opt/ngsep/NGSEPcore_5.0.0.jar"),
            vep_cache_dir=Path("/app/vep_cache"),
            vep_use_cache=False,
        )

    @pytest.fixture
    def service(self, config: PipelineConfig) -> PipelineService:
        """Create pipeline service instance."""
        return PipelineService(config)

    @pytest.fixture
    def sample(self) -> Sample:
        """Create test sample."""
        return Sample(
            id=uuid4(),
            patient_id=uuid4(),
            sample_code="12345",
            status=SampleStatus.PROCESSING,
        )

    @pytest.mark.asyncio
    async def test_prepare_sample_for_pipeline(
        self,
        service: PipelineService,
        config: PipelineConfig,
        sample: Sample,
        tmp_path: Path,
    ) -> None:
        """Test preparing sample files for pipeline execution."""
        # Create fake FASTQ files
        fastq_r1 = tmp_path / "test_R1.fastq.gz"
        fastq_r2 = tmp_path / "test_R2.fastq.gz"
        fastq_r1.write_text("fake fastq r1")
        fastq_r2.write_text("fake fastq r2")

        result_dir = await service.prepare_sample_for_pipeline(
            sample=sample,
            fastq_r1_path=fastq_r1,
            fastq_r2_path=fastq_r2,
        )

        # Verify directory structure
        assert result_dir.exists()
        assert (result_dir / "input").exists()

        # Verify FASTQ files were copied with correct naming
        expected_r1 = result_dir / "input" / f"{sample.sample_code}_S1_L001_R1_001.fastq.gz"
        expected_r2 = result_dir / "input" / f"{sample.sample_code}_S1_L001_R2_001.fastq.gz"
        assert expected_r1.exists()
        assert expected_r2.exists()
        # Files are gzipped, so we check they exist and have content
        assert expected_r1.stat().st_size > 0
        assert expected_r2.stat().st_size > 0

    def test_build_snakemake_command(
        self, service: PipelineService, config: PipelineConfig
    ) -> None:
        """Test building Snakemake command."""
        cmd = service._build_snakemake_command("12345")

        assert cmd[0] == "snakemake"
        assert "--snakefile" in cmd
        assert str(config.pipeline_script) in cmd
        assert "--configfile" in cmd
        # Runtime config is created dynamically, check it contains runtime_config.yaml
        configfile_idx = cmd.index("--configfile")
        assert "runtime_config.yaml" in cmd[configfile_idx + 1]
        assert "--cores" in cmd
        assert "4" in cmd
        # Check target path
        target = f"{config.results_path}/12345/variant_tables/12345_variants_raw.tsv"
        assert target in cmd

    def test_parse_pipeline_output(self, service: PipelineService, config: PipelineConfig) -> None:
        """Test parsing pipeline output files."""
        sample_id = uuid4()

        # Create fake variants file
        variants_content = """chrom\tpos_GRCh38\tref\talt\tgene\tvariant_type\ttranscript\texon/intron\tHGVS_VariantName\tdepth\tgenotype\tPopFreq_GNOMAD_v3.1.2\tACMG_classification\tvariant_caller\tgatk_depth\tgatk_allele_depth\tgatk_allele_fraction\tvariant_db_num\tvariant_db_hetero_num\tvariant_db_homo_num\tartifact_db_num\tis_variant\tis_artifact
1\t12345\tA\tG\tBRCA1\tSNV\tNM_007294.4\texon 10\tc.1234A>G\t100\t0/1\t0.001\tПатогенный\tgatk\t100\t50\t0.5\t10\t7\t3\t0\t\t
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(variants_content)
            variants_file = Path(f.name)

        # Create fake coverage file
        coverage_content = """0x_depth\t5x_depth\t30x_depth\t50x_depth\t100x_depth
100.0\t99.98\t95.5\t90.2\t75.3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(coverage_content)
            coverage_file = Path(f.name)

        try:
            variants, coverage = service.parse_pipeline_output(
                sample_id=sample_id,
                variants_file=variants_file,
                coverage_file=coverage_file,
            )

            # Verify variants
            assert len(variants) == 1
            assert variants[0].sample_id == sample_id
            assert variants[0].chromosome == "1"
            assert variants[0].gene == "BRCA1"

            # Verify coverage
            assert coverage is not None
            assert coverage.sample_id == sample_id
            assert coverage.depth_0x == Decimal("100.0")
            assert coverage.depth_30x == Decimal("95.5")
        finally:
            variants_file.unlink()
            coverage_file.unlink()

    def test_parse_pipeline_output_no_coverage(self, service: PipelineService) -> None:
        """Test parsing when coverage file doesn't exist."""
        sample_id = uuid4()

        variants_content = """chrom\tpos_GRCh38\tref\talt\tgene\tvariant_type\ttranscript\texon/intron\tHGVS_VariantName\tdepth\tgenotype\tPopFreq_GNOMAD_v3.1.2\tACMG_classification\tvariant_caller\tgatk_depth\tgatk_allele_depth\tgatk_allele_fraction\tvariant_db_num\tvariant_db_hetero_num\tvariant_db_homo_num\tartifact_db_num\tis_variant\tis_artifact
1\t12345\tA\tG\tBRCA1\tSNV\tNM\t\t\t50\t0/1\t\t\tgatk\t\t\t\t0\t0\t0\t0\t\t
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write(variants_content)
            variants_file = Path(f.name)

        try:
            variants, coverage = service.parse_pipeline_output(
                sample_id=sample_id,
                variants_file=variants_file,
                coverage_file=None,
            )

            assert len(variants) == 1
            assert coverage is None
        finally:
            variants_file.unlink()

    @pytest.mark.asyncio
    async def test_run_variant_calling_success(
        self, service: PipelineService, config: PipelineConfig
    ) -> None:
        """Test successful variant calling execution."""
        sample_code = "12345"

        # Create expected output directory and files
        sample_dir = config.results_path / sample_code / "variant_tables"
        sample_dir.mkdir(parents=True)
        variants_file = sample_dir / f"{sample_code}_variants_raw.tsv"
        coverage_file = sample_dir / f"{sample_code}_CovWidthAtDepths.tsv"
        variants_file.write_text("chrom\tpos_GRCh38\n1\t100\n")
        coverage_file.write_text("0x_depth\n100\n")

        # Create async iterator class for stdout
        class MockAsyncIterator:
            def __init__(self):
                self.items = [b"rule trim_fastq\n"]
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.stdout = MockAsyncIterator()
        mock_process.stderr = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await service.run_variant_calling(sample_code)

        assert result.success is True
        assert result.sample_code == sample_code
        assert result.variants_file == variants_file
        assert result.coverage_file == coverage_file

    @pytest.mark.asyncio
    async def test_run_variant_calling_failure(
        self, service: PipelineService, config: PipelineConfig
    ) -> None:
        """Test variant calling execution failure."""
        sample_code = "12345"

        # Create async iterator class for stdout (empty)
        class MockAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        # Mock subprocess failure
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.stdout = MockAsyncIterator()
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"Snakemake error")
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await service.run_variant_calling(sample_code)

        assert result.success is False
        assert result.sample_code == sample_code
        assert "Pipeline execution failed" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_run_variant_calling_with_progress(
        self, service: PipelineService, config: PipelineConfig
    ) -> None:
        """Test variant calling with progress callback."""
        sample_code = "12345"
        progress_calls = []

        # Create expected output
        sample_dir = config.results_path / sample_code / "variant_tables"
        sample_dir.mkdir(parents=True)
        (sample_dir / f"{sample_code}_variants_raw.tsv").write_text("chrom\n1\n")

        async def progress_callback(percent: int, message: str) -> None:
            progress_calls.append((percent, message))

        # Mock subprocess with progress output
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.stdout = AsyncMock()

        class MockAsyncIterator:
            def __init__(self):
                self.items = [
                    b"rule trim_fastq started\n",
                    b"rule map_fastq completed\n",
                    b"rule gatk_call_variants running\n",
                ]
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        mock_process.stdout = MockAsyncIterator()
        mock_process.stderr = AsyncMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await service.run_variant_calling(
                sample_code, progress_callback=progress_callback
            )

        assert result.success is True
        assert len(progress_calls) > 0
        # Check that progress was reported
        assert any(p[0] >= 5 for p in progress_calls)

    @pytest.mark.asyncio
    async def test_safe_callback_async(self, service: PipelineService) -> None:
        """Test safe callback with async function."""
        called = []

        async def async_callback(progress: int, message: str) -> None:
            called.append((progress, message))

        await service._safe_callback(async_callback, 50, "test message")

        assert called == [(50, "test message")]

    @pytest.mark.asyncio
    async def test_safe_callback_sync(self, service: PipelineService) -> None:
        """Test safe callback with sync function."""
        called = []

        def sync_callback(progress: int, message: str) -> None:
            called.append((progress, message))

        await service._safe_callback(sync_callback, 50, "test message")

        assert called == [(50, "test message")]

    @pytest.mark.asyncio
    async def test_safe_callback_error_handling(self, service: PipelineService) -> None:
        """Test safe callback handles errors gracefully."""

        def failing_callback(progress: int, message: str) -> None:
            raise ValueError("Callback failed")

        # Should not raise exception
        await service._safe_callback(failing_callback, 50, "test")


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful pipeline result."""
        result = PipelineResult(
            success=True,
            sample_code="12345",
            variants_file=Path("/path/to/variants.tsv"),
            coverage_file=Path("/path/to/coverage.tsv"),
            duration_seconds=3600,
        )

        assert result.success is True
        assert result.sample_code == "12345"
        assert result.variants_file == Path("/path/to/variants.tsv")
        assert result.error_message is None

    def test_failure_result(self) -> None:
        """Test failed pipeline result."""
        result = PipelineResult(
            success=False,
            sample_code="12345",
            error_message="Pipeline failed: memory error",
            duration_seconds=100,
        )

        assert result.success is False
        assert result.error_message == "Pipeline failed: memory error"
        assert result.variants_file is None
