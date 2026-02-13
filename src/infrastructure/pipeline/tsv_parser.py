"""TSV file parsers for pipeline output."""

import csv
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4

from src.domain.entities import RawVariant
from src.domain.enums import Sex, VariantType

logger = logging.getLogger(__name__)


@dataclass
class ParsedPatient:
    """Parsed patient data from TSV."""

    name: str
    sex: Sex
    birth_date: date
    request_id: str
    analysis_name: str


@dataclass
class ParsedVariant:
    """Parsed variant data from TSV."""

    chromosome: str
    position: int
    ref: str
    alt: str
    gene: str
    variant_type: VariantType
    transcript: str
    exon_intron: str | None
    hgvs: str | None
    genotype: str
    depth: int
    variant_caller: str
    gatk_depth: int | None
    gatk_allele_depth: int | None
    gatk_allele_fraction: Decimal | None
    variant_db_num: int
    variant_db_hetero_num: int
    variant_db_homo_num: int
    artifact_db_num: int


class TSVParser:
    """Parser for TSV files from pipeline."""

    # Column mappings (Russian to English)
    PATIENT_COLUMNS = {
        "ФИО": "name",
        "Пол": "sex",
        "Дата_рождения": "birth_date",
        "Номер_заявки": "request_id",
        "Наименование_исследования": "analysis_name",
    }

    VARIANT_COLUMNS = {
        "Chr": "chromosome",
        "Позиция": "position",
        "Ref": "ref",
        "Alt": "alt",
        "Ген": "gene",
        "Тип": "variant_type",
        "Транскрипт": "transcript",
        "Экзон/интрон": "exon_intron",
        "HGVS": "hgvs",
        "Зиготность": "genotype",
        "Глубина_покрытия": "depth",
        "Вариантные_колеры": "variant_caller",
        "GATK_глубина": "gatk_depth",
        "GATK_число_альтернативных_ридов": "gatk_allele_depth",
        "GATK_частота_альтернативного_аллеля": "gatk_allele_fraction",
        "Число_в_базе_вариантов": "variant_db_num",
        "Число_гетерозигот_в_базе": "variant_db_hetero_num",
        "Число_гомозигот_в_базе": "variant_db_homo_num",
        "Число_в_базе_артефактов": "artifact_db_num",
    }

    def parse_patients_tsv(self, file_path: str | Path) -> list[ParsedPatient]:
        """Parse patients TSV file.

        Args:
            file_path: Path to TSV file

        Returns:
            List of parsed patients
        """
        patients: list[ParsedPatient] = []
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return patients

        try:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")

                for row in reader:
                    try:
                        patient = self._parse_patient_row(row)
                        if patient:
                            patients.append(patient)
                    except Exception as e:
                        logger.warning(f"Failed to parse patient row: {e}")

        except Exception as e:
            logger.error(f"Failed to read patients TSV: {e}")

        logger.info(f"Parsed {len(patients)} patients from {file_path}")
        return patients

    def parse_variants_tsv(
        self,
        file_path: str | Path,
        sample_id: UUID | None = None,
    ) -> list[RawVariant]:
        """Parse variants TSV file.

        Args:
            file_path: Path to TSV file
            sample_id: Optional sample ID to associate variants with

        Returns:
            List of parsed raw variants
        """
        variants: list[RawVariant] = []
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return variants

        try:
            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")

                for row in reader:
                    try:
                        variant = self._parse_variant_row(row, sample_id)
                        if variant:
                            variants.append(variant)
                    except Exception as e:
                        logger.warning(f"Failed to parse variant row: {e}")

        except Exception as e:
            logger.error(f"Failed to read variants TSV: {e}")

        logger.info(f"Parsed {len(variants)} variants from {file_path}")
        return variants

    def _parse_patient_row(self, row: dict) -> ParsedPatient | None:
        """Parse a single patient row."""
        # Try to get values using both Russian and English column names
        name = row.get("ФИО") or row.get("name", "")
        if not name:
            return None

        sex_str = row.get("Пол") or row.get("sex", "")
        sex = Sex.from_string(sex_str)

        birth_date_str = row.get("Дата_рождения") or row.get("birth_date", "")
        birth_date = self._parse_date(birth_date_str)
        if not birth_date:
            return None

        request_id = row.get("Номер_заявки") or row.get("request_id", "")
        if not request_id:
            return None

        analysis_name = row.get("Наименование_исследования") or row.get("analysis_name", "")

        return ParsedPatient(
            name=name.strip(),
            sex=sex,
            birth_date=birth_date,
            request_id=request_id.strip(),
            analysis_name=analysis_name.strip(),
        )

    def _parse_variant_row(
        self,
        row: dict,
        sample_id: UUID | None,
    ) -> RawVariant | None:
        """Parse a single variant row."""
        # Get chromosome
        chrom = row.get("Chr") or row.get("chromosome", "")
        if not chrom:
            return None
        chrom = chrom.upper().replace("CHR", "")

        # Get position
        pos_str = row.get("Позиция") or row.get("position") or row.get("Start", "")
        try:
            position = int(pos_str)
        except (ValueError, TypeError):
            return None

        # Get ref/alt
        ref = row.get("Ref") or row.get("ref", "")
        alt = row.get("Alt") or row.get("alt", "")
        if not ref or not alt:
            return None

        # Get gene
        gene = row.get("Ген") or row.get("gene") or row.get("Gene", "")
        if not gene:
            gene = "Unknown"

        # Get variant type
        vtype_str = row.get("Тип") or row.get("variant_type") or row.get("ExonicFunc", "")
        variant_type = VariantType.from_string(vtype_str)

        # Get other fields
        transcript = row.get("Транскрипт") or row.get("transcript", "") or ""
        exon_intron = row.get("Экзон/интрон") or row.get("exon_intron") or None
        hgvs = row.get("HGVS") or row.get("hgvs") or None
        genotype = row.get("Зиготность") or row.get("genotype") or row.get("GT", "")

        # Parse numeric fields
        depth = self._safe_int(row.get("Глубина_покрытия") or row.get("depth") or row.get("DP", 0))
        variant_caller = row.get("Вариантные_колеры") or row.get("variant_caller", "")

        gatk_depth = self._safe_int(row.get("GATK_глубина") or row.get("gatk_depth"))
        gatk_allele_depth = self._safe_int(
            row.get("GATK_число_альтернативных_ридов") or row.get("gatk_allele_depth")
        )
        gatk_af_str = row.get("GATK_частота_альтернативного_аллеля") or row.get(
            "gatk_allele_fraction"
        )
        gatk_allele_fraction = self._safe_decimal(gatk_af_str)

        variant_db_num = self._safe_int(
            row.get("Число_в_базе_вариантов") or row.get("variant_db_num", 0)
        )
        variant_db_hetero = self._safe_int(
            row.get("Число_гетерозигот_в_базе") or row.get("variant_db_hetero_num", 0)
        )
        variant_db_homo = self._safe_int(
            row.get("Число_гомозигот_в_базе") or row.get("variant_db_homo_num", 0)
        )
        artifact_db_num = self._safe_int(
            row.get("Число_в_базе_артефактов") or row.get("artifact_db_num", 0)
        )

        return RawVariant(
            id=uuid4(),
            sample_id=sample_id,
            chromosome=chrom,
            position=position,
            ref=ref.upper(),
            alt=alt.upper(),
            gene=gene.upper(),
            variant_type=variant_type,
            transcript=transcript,
            exon_intron=exon_intron,
            hgvs=hgvs,
            genotype=genotype,
            depth=depth,
            variant_caller=variant_caller,
            gatk_depth=gatk_depth,
            gatk_allele_depth=gatk_allele_depth,
            gatk_allele_fraction=gatk_allele_fraction,
            variant_db_num=variant_db_num,
            variant_db_hetero_num=variant_db_hetero,
            variant_db_homo_num=variant_db_homo,
            artifact_db_num=artifact_db_num,
        )

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date from string (supports multiple formats)."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Try ISO format first
        if "-" in date_str:
            try:
                return date.fromisoformat(date_str)
            except ValueError:
                pass

        # Try other formats
        formats = [
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y.%m.%d",
        ]

        from datetime import datetime as dt

        for fmt in formats:
            try:
                return dt.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _safe_int(self, value) -> int:
        """Safely convert value to int."""
        if value is None or value == "":
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _safe_decimal(self, value) -> Decimal | None:
        """Safely convert value to Decimal."""
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None


# Singleton instance
tsv_parser = TSVParser()
