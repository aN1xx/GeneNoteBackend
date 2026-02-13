"""Report generation service using ReportLab.

Generates PDF reports for genetic analysis results with:
- Patient and sample information header
- Logo and page numbering
- Variants table with ACMG classification coloring
- Analysis information (WetLab info, coverage stats)

Based on Functions_MakeReport.py from the original pipeline.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

try:
    from PyPDF2 import PdfReader, PdfWriter

    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from pdfrw import PdfReader as pdfrw_PdfReader
    from pdfrw.buildxobj import pagexobj
    from pdfrw.toreportlab import makerl

    HAS_PDFRW = True
except ImportError:
    HAS_PDFRW = False

from src.domain.entities import Patient, Sample, SampleCoverage, SampleVariant
from src.domain.enums import ACMGClassification

logger = logging.getLogger(__name__)

# Amino acid 3-letter to 1-letter mapping (IUPAC standard)
AMINO_ACID_3TO1 = {
    "Ala": "A",
    "Asx": "B",
    "Cys": "C",
    "Asp": "D",
    "Glu": "E",
    "Phe": "F",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Lys": "K",
    "Leu": "L",
    "Met": "M",
    "Asn": "N",
    "Pro": "P",
    "Gln": "Q",
    "Arg": "R",
    "Ser": "S",
    "Thr": "T",
    "Sec": "U",
    "Val": "V",
    "Trp": "W",
    "Xaa": "X",
    "Tyr": "Y",
    "Glx": "Z",
    "Ter": "*",  # Stop codon
}


def convert_amino_acids_3to1(hgvs: str) -> str:
    """Convert 3-letter amino acid codes to 1-letter codes in HGVS notation.

    Args:
        hgvs: HGVS notation string (e.g., "p.Ala123Val")

    Returns:
        HGVS with 1-letter amino acid codes (e.g., "p.A123V")
    """
    result = hgvs
    for aa3, aa1 in AMINO_ACID_3TO1.items():
        result = result.replace(aa3, aa1)
    return result


def format_hgvs_for_display(hgvs: str | None) -> str:
    """Format HGVS notation for PDF display with line breaks.

    Args:
        hgvs: HGVS notation string

    Returns:
        Formatted HGVS with line breaks for protein change
    """
    if not hgvs:
        return ""

    # Convert 3-letter to 1-letter amino acids
    formatted = convert_amino_acids_3to1(hgvs)

    # Add line break before protein change
    if "(" in formatted:
        parts = formatted.split("(")
        if len(parts) > 1:
            formatted = "<br/>(".join(parts)

    return formatted


def format_exon_intron(exon_intron: str | None) -> str:
    """Format exon/intron for display with line breaks.

    Args:
        exon_intron: Exon/intron string (e.g., "экзон 10")

    Returns:
        Formatted string with line break
    """
    if not exon_intron:
        return ""

    parts = exon_intron.split(" ")
    return "<br/>".join(parts) if len(parts) > 1 else exon_intron


def format_gnomad_frequency(value: Decimal | float | None) -> str:
    """Format gnomAD frequency for display with appropriate precision.

    Args:
        value: Frequency value (0-1 range)

    Returns:
        Formatted percentage string
    """
    if value is None or value == 0:
        return "0.00%"

    val = float(value)
    if val == 0:
        return "0.00%"

    # Find first significant digit
    val_str = str(val)
    if "." not in val_str:
        return f"{val * 100:.2f}%"

    # Determine required decimal places
    # Multiply by 100 for percentage
    percent = val * 100

    if percent >= 1:
        return f"{percent:.2f}%"
    elif percent >= 0.1:
        return f"{percent:.3f}%"
    elif percent >= 0.01:
        return f"{percent:.4f}%"
    else:
        # Find first significant digit after decimal
        decimal_part = val_str.split(".")[-1] if "." in val_str else "0"
        significant_pos = 0
        for i, c in enumerate(decimal_part):
            if c != "0":
                significant_pos = i
                break

        # Calculate required decimal places after multiplying by 100
        required_decimals = max(significant_pos - 1, 2)
        return f"{percent:.{required_decimals}f}%"


def split_thousands(num: int) -> str:
    """Format number with thousand separators.

    Args:
        num: Integer number

    Returns:
        Formatted string with spaces as thousand separators
    """
    num_str = str(num)[::-1]
    chunks = [num_str[i : i + 3] for i in range(0, len(num_str), 3)]
    return " ".join(chunks)[::-1]


class ConditionalSpacer(Flowable):
    """Custom flowable for conditional spacing or page break."""

    def __init__(self, spacer_height: float = 30, threshold: float = 150) -> None:
        super().__init__()
        self.spacer_height = spacer_height
        self.threshold = threshold
        self.width = 0.0
        self.height = 0.0
        self.use_page_break = False

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:
        """Determine spacing based on available height."""
        if availHeight >= self.threshold:
            self.height = self.spacer_height
            self.use_page_break = False
        else:
            self.height = availHeight
            self.use_page_break = True
        return (0, self.height)

    def draw(self) -> None:
        """Draw method - nothing to draw, spacing handled by wrap."""
        pass


def _find_cyrillic_font(font_path: Path | str | None = None) -> tuple[str, Path | None]:
    """Find a font with Cyrillic support.

    Args:
        font_path: Optional explicit font path from config

    Returns:
        Tuple of (font_name, font_path_used)
    """
    # Common font names with Cyrillic support
    cyrillic_fonts = [
        "SegoeUI",
        "segoeui",
        "DejaVuSans",
        "DejaVuSansCondensed",
        "LiberationSans",
        "ArialUnicodeMS",
        "NotoSans-Regular",
        "Roboto-Regular",
    ]

    # Standard font paths on different systems (SegoeUI first as preferred for reports)
    font_paths = [
        # SegoeUI - preferred font (used in original pipeline)
        Path("~/.fonts/segoeui/segoeui.ttf").expanduser(),
        Path("/usr/share/fonts/truetype/segoeui/segoeui.ttf"),
        Path("/usr/local/share/fonts/segoeui/segoeui.ttf"),
        # DejaVu fonts (good fallback with Cyrillic support)
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),  # macOS
        Path("C:/Windows/Fonts/arial.ttf"),  # Windows
        Path("C:/Windows/Fonts/arialuni.ttf"),  # Windows Arial Unicode
        Path("C:/Windows/Fonts/segoeui.ttf"),  # Windows SegoeUI
    ]

    # If explicit font path provided, use it first
    if font_path:
        font_path_obj = Path(font_path)
        if font_path_obj.exists():
            try:
                font_name = "CyrillicFont"
                pdfmetrics.registerFont(TTFont(font_name, str(font_path_obj)))
                logger.info(f"Using configured Cyrillic font: {font_path_obj}")
                return font_name, font_path_obj
            except Exception as e:
                logger.warning(f"Failed to load configured font {font_path_obj}: {e}")

    # Try to find system fonts with Cyrillic support
    for font_path_obj in font_paths:
        if font_path_obj.exists():
            try:
                # Use "SegoeUI" for segoeui font files (matching original pipeline)
                stem_lower = font_path_obj.stem.lower()
                if "segoe" in stem_lower:
                    font_name = "SegoeUI"
                else:
                    font_name = font_path_obj.stem.replace("-", "").replace("_", "")
                pdfmetrics.registerFont(TTFont(font_name, str(font_path_obj)))
                logger.info(f"Found and registered Cyrillic font: {font_path_obj}")
                return font_name, font_path_obj
            except Exception as e:
                logger.debug(f"Failed to load font {font_path_obj}: {e}")
                continue

    # Try to find fonts in common user font directories
    user_font_dirs = [
        Path.home() / ".fonts",
        Path.home() / "Library/Fonts",  # macOS
        Path("/usr/local/share/fonts"),
    ]

    for font_dir in user_font_dirs:
        if not font_dir.exists():
            continue
        for font_name in cyrillic_fonts:
            # Try different extensions
            for ext in [".ttf", ".otf"]:
                font_path_obj = font_dir / f"{font_name}{ext}"
                if font_path_obj.exists():
                    try:
                        # Use "SegoeUI" for segoe fonts (matching original pipeline)
                        if "segoe" in font_name.lower():
                            registered_name = "SegoeUI"
                        else:
                            registered_name = font_name.replace("-", "").replace("_", "")
                        pdfmetrics.registerFont(TTFont(registered_name, str(font_path_obj)))
                        logger.info(f"Found and registered Cyrillic font: {font_path_obj}")
                        return registered_name, font_path_obj
                    except Exception as e:
                        logger.debug(f"Failed to load font {font_path_obj}: {e}")
                        continue

    # Fallback: try to use built-in ReportLab fonts that might support Cyrillic
    # Note: Helvetica does NOT support Cyrillic, but we'll log a warning
    logger.warning(
        "No Cyrillic font found. Russian text may display as dots. "
        "Please install a font with Cyrillic support (e.g., DejaVu Sans) or "
        "configure pdf_font_path in settings."
    )
    return "Helvetica", None


class ReportGenerator:
    """Generates PDF reports for genetic analysis results.

    Features:
    - Patient and sample information header
    - Optional logo overlay
    - Page numbering
    - Variants table with ACMG classification coloring
    - WetLab information and coverage statistics
    - HGVS notation with 1-letter amino acid codes
    """

    # ACMG classification sort order
    ACMG_ORDER = [
        ACMGClassification.PATHOGENIC,
        ACMGClassification.LIKELY_PATHOGENIC,
        ACMGClassification.VUS,
        ACMGClassification.LIKELY_BENIGN,
        ACMGClassification.BENIGN,
    ]

    # WetLab information
    WETLAB_INFO = [
        "Исследование выполнено с использованием набора «Quasar-BRCA1/2» "
        "(ТестГен, Россия) на приборе MiSeq (Illumina, USA).",
        "Панель покрывает все кодирующие экзоны генов BRCA1 и BRCA2 и не менее "
        "20 пар нуклеотидов во фланкирующих областях с каждой стороны экзонов.",
    ]

    # Resequencing notice for low quality samples
    RESEQUENCING_NOTICE = (
        "Полученные результаты секвенирования не позволяют достоверно оценить "
        "наличие или отсутствие патогенных и вероятно патогенных генетических "
        "вариантов. Необходимо выполнить повторное секвенирование образца."
    )

    def __init__(
        self,
        font_path: str | Path | None = None,
        logo_path: str | Path | None = None,
    ) -> None:
        """Initialize report generator.

        Args:
            font_path: Path to TTF font file (optional). If not provided,
                      will attempt to find a system font with Cyrillic support.
            logo_path: Path to logo PDF file (optional). If provided,
                      logo will be added to every page.
        """
        self.font_name, self.font_path = _find_cyrillic_font(font_path)
        self.logo_path = Path(logo_path) if logo_path else None

        if self.logo_path and not self.logo_path.exists():
            logger.warning(f"Logo file not found: {self.logo_path}")
            self.logo_path = None

    def generate_report(
        self,
        sample: Sample,
        patient: Patient,
        variants: list[SampleVariant],
        coverage: SampleCoverage | None,
        output_path: Path,
        read_stats: dict | None = None,
        low_quality: bool = False,
    ) -> Path:
        """Generate PDF report for a sample.

        Args:
            sample: Sample entity
            patient: Patient entity
            variants: List of confirmed variants (is_variant=True)
            coverage: Coverage data (optional)
            output_path: Output file path
            read_stats: Optional read statistics from fastp JSON
            low_quality: If True, generates a resequencing notice report

        Returns:
            Path to generated PDF
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        page_width, page_height = landscape(A4)

        # Generate report body first
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=(page_width, page_height),
            topMargin=101,
            bottomMargin=47,
            leftMargin=52,
            rightMargin=52,
        )

        # Build report elements
        elements = []

        if low_quality:
            # Generate resequencing notice report
            elements.extend(self._build_resequencing_notice())
        else:
            # Add variants table if any
            if variants:
                elements.append(self._build_variants_table(variants))

                # Add conditional spacer for analysis info
                spacer_height = 30
                info_height = 10 + 14 * (len(self.WETLAB_INFO) + 5)  # Approximate
                min_space_required = spacer_height + info_height + 47
                elements.append(
                    ConditionalSpacer(spacer_height=spacer_height, threshold=min_space_required)
                )

            # Add analysis info
            elements.extend(self._build_analysis_info(coverage, read_stats))

        # Build PDF
        doc.build(elements)

        # Add header, logo and page numbers using overlay
        header_lines = self._get_header_lines(patient, sample)
        self._add_header_and_page_numbers(output_path, header_lines)

        return output_path

    def generate_resequencing_report(
        self,
        sample: Sample,
        patient: Patient,
        output_path: Path,
    ) -> Path:
        """Generate a resequencing notice report for low quality samples.

        Args:
            sample: Sample entity
            patient: Patient entity
            output_path: Output file path

        Returns:
            Path to generated PDF
        """
        return self.generate_report(
            sample=sample,
            patient=patient,
            variants=[],
            coverage=None,
            output_path=output_path,
            low_quality=True,
        )

    def generate_report_bytes(
        self,
        sample: Sample,
        patient: Patient,
        variants: list[SampleVariant],
        coverage: SampleCoverage | None,
        read_stats: dict | None = None,
    ) -> bytes:
        """Generate PDF report and return as bytes.

        Args:
            sample: Sample entity
            patient: Patient entity
            variants: List of confirmed variants
            coverage: Coverage data (optional)
            read_stats: Optional read statistics from fastp JSON

        Returns:
            PDF as bytes
        """
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            self.generate_report(
                sample=sample,
                patient=patient,
                variants=variants,
                coverage=coverage,
                output_path=tmp_path,
                read_stats=read_stats,
            )

            return tmp_path.read_bytes()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _get_header_lines(self, patient: Patient, sample: Sample) -> list[str]:
        """Get header lines for the report.

        Args:
            patient: Patient entity
            sample: Sample entity

        Returns:
            List of header lines
        """
        sex_address = "Пациентка" if patient.sex.value == "ж" else "Пациент"
        birth_date_str = patient.birth_date.strftime("%d.%m.%Y") if patient.birth_date else ""

        # Get base request_id without version suffix
        base_request_id = sample.sample_code.split(".")[0]

        return [
            f"{sex_address}: {patient.name} {birth_date_str}. № пробы: {base_request_id}",
            "Развёрнутый отчёт по результатам исследования",
            patient.analysis_name or "",
        ]

    def _add_header_and_page_numbers(  # noqa: PLR0915
        self, report_path: Path, header_lines: list[str]
    ) -> None:
        """Add header, logo and page numbers to each page of the report.

        Uses PyPDF2 and pdfrw to overlay header and page numbers.

        Args:
            report_path: Path to the PDF file to modify
            header_lines: Header lines to add
        """
        if not HAS_PYPDF2:
            logger.warning("PyPDF2 not installed. Header and page numbers will not be added.")
            return

        page_width, page_height = landscape(A4)

        # Margins and font settings
        header_side_margin = 57
        header_top_margin = 47
        page_num_bottom_margin = 32
        page_num_side_margin = page_width - header_side_margin
        header_font_size = 9
        header_line_vertical_space = 20
        page_num_font_size = 9

        # Logo settings
        logo_width, logo_height = 145, 45.5
        logo_x = page_width - logo_width - header_side_margin
        logo_y = page_height - logo_height - header_top_margin + header_font_size

        # Read original PDF
        reader = PdfReader(str(report_path))
        writer = PdfWriter()
        page_num = len(reader.pages)

        # Load logo if available
        logo_xobj = None
        logo_scale_x = logo_scale_y = 1.0
        if self.logo_path and HAS_PDFRW:
            try:
                logo_xobj = pagexobj(pdfrw_PdfReader(str(self.logo_path)).pages[0])
                orig_logo_width = logo_xobj.BBox[2] - logo_xobj.BBox[0]
                orig_logo_height = logo_xobj.BBox[3] - logo_xobj.BBox[1]
                logo_scale_x = logo_width / orig_logo_width
                logo_scale_y = logo_height / orig_logo_height
            except Exception as e:
                logger.warning(f"Failed to load logo: {e}")
                logo_xobj = None

        # Create overlay for each page
        overlay_pdfs = []
        for page_i in range(page_num):
            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=landscape(A4))

            # Draw logo if available
            if logo_xobj:
                logo_form_name = makerl(c, logo_xobj)
                c.saveState()
                c.translate(logo_x, logo_y)
                c.scale(logo_scale_x, logo_scale_y)
                c.doForm(logo_form_name)
                c.restoreState()

            # Write header
            c.setFont(self.font_name, header_font_size)
            header_line_y = page_height - header_top_margin
            for header_line in header_lines:
                if header_line:
                    c.drawString(header_side_margin, header_line_y, header_line)
                    header_line_y -= header_line_vertical_space

            # Write generation timestamp (bottom left) in UTC+5
            c.setFont(self.font_name, page_num_font_size)
            utc_plus_5 = timezone(timedelta(hours=5))
            timestamp = datetime.now(utc_plus_5).strftime("%d.%m.%Y в %H:%M:%S")
            timestamp_txt = f"Отчет сформирован {timestamp} (UTC+5)"
            c.drawString(header_side_margin, page_num_bottom_margin, timestamp_txt)

            # Write page number (bottom right)
            page_num_txt = f"Лист {page_i + 1} из {page_num}"
            c.drawRightString(page_num_side_margin, page_num_bottom_margin, page_num_txt)

            c.save()
            packet.seek(0)
            overlay_pdfs.append(PdfReader(packet))

        # Overlay pages
        for page_i in range(page_num):
            original_page = reader.pages[page_i]
            overlay_page = overlay_pdfs[page_i].pages[0]
            original_page.merge_page(overlay_page)
            writer.add_page(original_page)

        # Write final PDF
        with open(report_path, "wb") as f:
            writer.write(f)

    def _build_resequencing_notice(self) -> list[Paragraph]:
        """Build resequencing notice for low quality samples.

        Returns:
            List of paragraph elements
        """
        info_style = ParagraphStyle(
            name="InfoStyle",
            fontName=self.font_name,
            fontSize=9,
            leading=13,
        )

        return [Paragraph(self.RESEQUENCING_NOTICE, info_style)]

    def _build_variants_table(self, variants: list[SampleVariant]) -> Table:
        """Build variants table with proper formatting.

        Table includes:
        - Chromosome, Position, Ref, Alt
        - Gene, Variant type, Transcript
        - Exon/Intron, HGVS name
        - Depth, Genotype
        - gnomAD frequency, ACMG classification

        Variants are sorted by ACMG classification (pathogenic first).
        Pathogenic and likely pathogenic variants are highlighted in red.
        """
        table_style = ParagraphStyle(
            name="TableStyle",
            fontName=self.font_name,
            fontSize=8,
            alignment=TA_CENTER,
            wordWrap="CJK",
        )

        # Sort variants by ACMG classification
        sorted_variants = sorted(
            variants,
            key=lambda v: (
                self.ACMG_ORDER.index(v.acmg_classification)
                if v.acmg_classification in self.ACMG_ORDER
                else len(self.ACMG_ORDER),
                str(v.chromosome),
                v.position,
            ),
        )

        # Row height - fixed since ref/alt are always truncated to max 6 chars ("ABC...")
        row_heights = 36

        # Header row (matching original Functions_MakeReport.py)
        headers = [
            "Хромосома",
            "Позиция<br/>(hg38)",
            "Реф.<br/>аллель",
            "Обн.<br/>аллель",
            "Ген",
            "Тип варианта",
            "Транскрипт",
            "Экзон/<br/>интрон",
            "Наименование<br/>варианта",
            "Глубина<br/>прочтения",
            "Генотип",
            "Популяционная<br/>частота<br/>(gnomAD v.3.1.2)",
            "Классификация<br/>варианта по ACMG",
        ]
        header_row = [Paragraph(h, table_style) for h in headers]

        # Data rows
        def truncate_allele(allele: str, max_len: int = 3) -> str:
            """Truncate allele to max_len chars with ellipsis if longer."""
            if len(allele) > max_len:
                return allele[:max_len] + "..."
            return allele

        data_rows = []
        for v in sorted_variants:
            gnomad_str = format_gnomad_frequency(v.pop_freq_gnomad)
            acmg_str = self._format_acmg(v.acmg_classification)
            hgvs_str = format_hgvs_for_display(v.hgvs)
            exon_intron_str = format_exon_intron(v.exon_intron)

            row = [
                Paragraph(str(v.chromosome), table_style),
                Paragraph(str(v.position), table_style),
                Paragraph(truncate_allele(v.ref), table_style),
                Paragraph(truncate_allele(v.alt), table_style),
                Paragraph(v.gene, table_style),
                Paragraph(v.variant_type or "", table_style),
                Paragraph(v.transcript or "", table_style),
                Paragraph(exon_intron_str, table_style),
                Paragraph(hgvs_str, table_style),
                Paragraph(str(v.depth), table_style),
                Paragraph(v.genotype, table_style),
                Paragraph(gnomad_str, table_style),
                Paragraph(acmg_str, table_style),
            ]
            data_rows.append(row)

        table_data = [header_row, *data_rows]

        # Column widths (matching original)
        col_widths = [51, 45, 34, 34, 32, 74, 60, 40, 82, 50, 60, 72, 92]

        table = Table(table_data, repeatRows=1, colWidths=col_widths, rowHeights=row_heights)

        # Table styling
        style_commands = [
            ("GRID", (0, 0), (-1, -1), 0.9, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]

        # Color pathogenic variants
        light_red = colors.HexColor("#F7BAA9")
        for i, v in enumerate(sorted_variants, start=1):
            if v.acmg_classification in [
                ACMGClassification.PATHOGENIC,
                ACMGClassification.LIKELY_PATHOGENIC,
            ]:
                style_commands.append(("BACKGROUND", (0, i), (-1, i), light_red))

        table.setStyle(TableStyle(style_commands))
        return table

    def _build_analysis_info(
        self,
        coverage: SampleCoverage | None,
        read_stats: dict | None = None,
    ) -> list[Paragraph | KeepTogether]:
        """Build analysis info paragraphs.

        Includes:
        - WetLab information (kit, sequencer, panel coverage)
        - Read statistics (if provided)
        - Coverage at different depths

        Args:
            coverage: Sample coverage data
            read_stats: Optional fastp JSON read statistics

        Returns:
            List of paragraph elements
        """
        info_style = ParagraphStyle(
            name="InfoStyle",
            fontName=self.font_name,
            fontSize=9,
            leading=13,
        )

        lines = list(self.WETLAB_INFO)

        # Add read statistics if available
        if read_stats:
            try:
                summary = read_stats.get("summary", {}).get("after_filtering", {})
                total_reads = summary.get("total_reads", 0)
                total_bases = summary.get("total_bases", 0)

                if total_reads > 0:
                    read_pairs = total_reads // 2
                    lines.append(f"Общее число парных прочтений – {split_thousands(read_pairs)}")
                if total_bases > 0:
                    lines.append(
                        f"Общее число прочитанных нуклеотидов – {split_thousands(total_bases)}"
                    )
            except (KeyError, TypeError) as e:
                logger.debug(f"Failed to parse read stats: {e}")

        # Add coverage statistics
        if coverage:
            lines.extend(
                [
                    f"Покрытие x>30 – {int(coverage.depth_30x)}%",
                    f"Покрытие x>50 – {int(coverage.depth_50x)}%",
                    f"Покрытие x>100 – {int(coverage.depth_100x)}%",
                ]
            )

        paragraphs = [Paragraph(line, info_style) for line in lines]
        return [KeepTogether(paragraphs)]

    def _format_acmg(self, classification: ACMGClassification | None) -> str:
        """Format ACMG classification for display with line breaks.

        Args:
            classification: ACMG classification enum

        Returns:
            Formatted classification string for PDF display
        """
        if not classification:
            return ""

        mapping = {
            ACMGClassification.PATHOGENIC: "Патогенный",
            ACMGClassification.LIKELY_PATHOGENIC: "Вероятно<br/>патогенный",
            ACMGClassification.VUS: "Вариант неясного<br/>клинического значения",
            ACMGClassification.LIKELY_BENIGN: "Вероятно<br/>доброкачественный",
            ACMGClassification.BENIGN: "Доброкачественный",
        }
        return mapping.get(classification, classification.value)
