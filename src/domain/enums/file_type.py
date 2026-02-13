"""File type enumeration."""

from enum import StrEnum


class FileType(StrEnum):
    """Types of files in the system."""

    # Input files
    TSV_PATIENTS = "tsv_patients"
    FASTQ_R1 = "fastq_r1"
    FASTQ_R2 = "fastq_r2"

    # Intermediate files
    BAM = "bam"
    BAM_INDEX = "bam_index"
    VCF = "vcf"
    VCF_GATK = "vcf_gatk"
    VCF_NGSEP = "vcf_ngsep"
    VCF_XATLAS = "vcf_xatlas"
    TSV_RAW_VARIANTS = "tsv_raw_variants"
    TSV_DEPTH_COVERAGE = "tsv_depth_coverage"

    # Output files
    TSV_ANNOTATED_VARIANTS = "tsv_annotated_variants"
    PDF_REPORT = "pdf_report"

    # Other
    JSON_TRIM_STATS = "json_trim_stats"
    HTML_FASTP_REPORT = "html_fastp_report"

    def is_input(self) -> bool:
        """Check if file type is input."""
        return self in (FileType.TSV_PATIENTS, FileType.FASTQ_R1, FileType.FASTQ_R2)

    def is_output(self) -> bool:
        """Check if file type is final output."""
        return self in (FileType.TSV_ANNOTATED_VARIANTS, FileType.PDF_REPORT)

    def get_extension(self) -> str:
        """Get file extension for this type."""
        extensions = {
            FileType.TSV_PATIENTS: ".tsv",
            FileType.FASTQ_R1: ".fastq.gz",
            FileType.FASTQ_R2: ".fastq.gz",
            FileType.BAM: ".bam",
            FileType.BAM_INDEX: ".bai",
            FileType.VCF: ".vcf",
            FileType.VCF_GATK: ".vcf",
            FileType.VCF_NGSEP: ".vcf",
            FileType.VCF_XATLAS: ".vcf",
            FileType.TSV_RAW_VARIANTS: ".tsv",
            FileType.TSV_DEPTH_COVERAGE: ".tsv",
            FileType.TSV_ANNOTATED_VARIANTS: ".tsv",
            FileType.PDF_REPORT: ".pdf",
            FileType.JSON_TRIM_STATS: ".json",
            FileType.HTML_FASTP_REPORT: ".html",
        }
        return extensions.get(self, "")


class SampleStatus(StrEnum):
    """Status of a sample."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    AWAITING_ANNOTATION = "awaiting_annotation"
    ANNOTATED = "annotated"
    REPORT_GENERATED = "report_generated"
    FAILED = "failed"
