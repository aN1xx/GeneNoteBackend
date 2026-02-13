import json

import pandas as pd

from math import ceil

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from PyPDF2 import PdfWriter, PdfReader

from io import BytesIO
from pathlib import Path

from pdfrw import PdfReader as pdfrw_PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl


def _find_segoeui_font():
    """Find SegoeUI font file across common system paths."""
    candidates = [
        Path("~/.fonts/segoeui/segoeui.ttf").expanduser(),
        Path("/usr/share/fonts/truetype/segoeui/segoeui.ttf"),
        Path("/usr/local/share/fonts/segoeui/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    raise FileNotFoundError(
        "No suitable font found. Install SegoeUI to ~/.fonts/segoeui/segoeui.ttf "
        "or DejaVu Sans to /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )




# Extract info for report lines -------------------------------------------------------------------------------------------------------
def get_DepthAtCovPercent_lst(depth_filepath):
    depth_df = pd.read_csv(depth_filepath, sep='\t')
    Depth30xCov_percent = int(depth_df.loc[0, '30x_depth'])
    Depth50xCov_percent = int(depth_df.loc[0, '50x_depth'])
    Depth100xCov_percent = int(depth_df.loc[0, '100x_depth'])
    DepthAtCovPercent_lst = [f'Покрытие x>30 – {Depth30xCov_percent}%',
                             f'Покрытие x>50 – {Depth50xCov_percent}%',
                             f'Покрытие x>100 – {Depth100xCov_percent}%']
    return DepthAtCovPercent_lst

# def get_ReadStats_lst ---------------------------------------------------------------------------------------------------------------
def split_thousands(num):
    num = str(num)
    num = num[::-1]
    cnt = 0
    splited_num = []
    for elem in num:
        cnt += 1
        splited_num.append(elem)
        if cnt == 3:
            splited_num.append(' ')
            cnt = 0
    num = ''.join(splited_num)
    num = num[::-1]
    return num

def get_ReadStats_lst(ReadStats_filepath):
    with open(ReadStats_filepath, 'r') as handle:
        ReadStats = json.load(handle)
    ReadPair_num = int(ReadStats['summary']['after_filtering']['total_reads'] / 2)
    ReadPair_num = split_thousands(ReadPair_num)
    base_num = ReadStats['summary']['after_filtering']['total_bases']
    base_num = split_thousands(base_num)
    ReadStats_lst = [f'Общее число парных прочтений – {ReadPair_num}',
                     f'Общее число прочитанных нуклеотидов – {base_num}']
    return ReadStats_lst
# def get_ReadStats_lst ---------------------------------------------------------------------------------------------------------------

def get_PatientInfo_PatientAnalysis_lines(sample, patients_df):
    patient_row = patients_df[patients_df['request_id'].str.contains(sample)].squeeze()
    # Patient info line
    patient_name = patient_row['name']
    patient_BirthDate = patient_row['birth_date']
    patient_sex = patient_row['sex']
    address_patient = 'Пациентка' if patient_sex == 'ж' else 'Пациент'
    PatientInfo_line = f'{address_patient}: {patient_name} {patient_BirthDate}. № пробы: {sample.split('.')[0]}'
    # Patient analysis line
    PatientAnalysis_line = patient_row['analysis_name']
    return PatientInfo_line, PatientAnalysis_line
# Extract info for report lines -------------------------------------------------------------------------------------------------------




# Make report paragraphs --------------------------------------------------------------------------------------------------------------
def make_header_lst(PatientInfo_line, PatientAnalysis_line):
    header_lst = [PatientInfo_line,
                  'Развёрнутый отчёт по результатам исследования',
                  PatientAnalysis_line]
    return header_lst

def make_AnalysisInfo_lst(ReadStats_lst, DepthAtCovPercent_lst):
    KitSequencerInfo_line = 'Исследование выполнено с использованием набора «Quasar-BRCA1/2» (ТестГен, Россия) на приборе MiSeq (Illumina, USA).'
    GenePanelInfo_line = 'Панель покрывает все кодирующие экзоны генов BRCA1 и BRCA2 и не менее 20 пар нуклеотидов во фланкирующих областях с каждой стороны экзонов.'
    WetLabInfo_lst = [KitSequencerInfo_line, GenePanelInfo_line]
    AnalysisInfo_lst = WetLabInfo_lst + ReadStats_lst + DepthAtCovPercent_lst
    return AnalysisInfo_lst
# Make report paragraphs --------------------------------------------------------------------------------------------------------------




# DEF write_info_and_table ------------------------------------------------------------------------------------------------------------
# DEF make_Platypus_table -------------------------------------------------------------------------------------------------------------
def ama_3letter_to_1letter(hgvs):
    # https://iupac.qmul.ac.uk/AminoAcid/A2021.html
    map_3letter_1letter = {'Ala': 'A', 'Asx': 'B', 'Cys': 'C', 'Asp': 'D', 'Glu': 'E', 'Phe': 'F', 'Gly': 'G', 'His': 'H', 'Ile': 'I',
                           'Lys': 'K', 'Leu': 'L', 'Met': 'M', 'Asn': 'N', 'Pro': 'P', 'Gln': 'Q', 'Arg': 'R', 'Ser': 'S', 'Thr': 'T',
                           'Sec': 'U', 'Val': 'V', 'Trp': 'W', 'Xaa': 'X', 'Tyr': 'Y', 'Glx': 'Z'}
    for ama_3letter in map_3letter_1letter.keys():
        ama_1letter = map_3letter_1letter[ama_3letter]
        hgvs = hgvs.replace(ama_3letter, ama_1letter)
    return hgvs

def insert_br_to_hgvs(hgvs):
    new_hgvs = hgvs[::]
    hgvs_lst = hgvs.split('(')
    if len(hgvs_lst) > 1:
        new_hgvs = '<br/>('.join(hgvs_lst)
    return new_hgvs

def insert_br_to_ExonOrIntron(ExonOrIntron):
    ExonOrIntron = ExonOrIntron.split(' ')
    ExonOrIntron = '<br/>'.join(ExonOrIntron)
    return ExonOrIntron

def round_gnomad(val):
    if val == 0:
        return '0.00%'
    val = str(val)
    el_i = 2
    el = val[el_i]
    while el == '0':
        el_i += 1
        el = val[el_i]
    if el_i == 3:
        whole_digit_num = 1
    elif el_i == 2:
        whole_digit_num = 2
    else:
        whole_digit_num = 0
    required_decimal_places = el_i - 2 + whole_digit_num # minus 2 decimal places because of multiplying by 100
    rounded_val = round(float(val) * 100, required_decimal_places)
    rounded_val = f"{rounded_val:.{required_decimal_places}f}%"
    return rounded_val

def insert_br_to_ACMG(acmg):
    if acmg in ['Вероятно патогенный', 'Вероятно доброкачественный']:
        acmg = acmg.split(' ')
        acmg = '<br/>'.join(acmg)
    elif acmg == 'Вариант неясного клинического значения':
        acmg = 'Вариант неясного<br/>клинического значения'
    return acmg

def color_table_cells(variants_df):
    light_red = colors.HexColor("#F7BAA9")
    acmg_classifications = variants_df['ACMG_classification']
    Table_Style_colors = []
    for row_i, acmg_classification in enumerate(acmg_classifications):
        row_i += 1
        if acmg_classification == "Вероятно патогенный":
            row_color = ('BACKGROUND', (0, row_i), (-1, row_i), light_red)
            Table_Style_colors.append(row_color)
        elif acmg_classification == "Патогенный":
            row_color = ('BACKGROUND', (0, row_i), (-1, row_i), light_red)
            Table_Style_colors.append(row_color)
    return Table_Style_colors
    

def make_Platypus_table(variants_df, table_style):
    # Calculate row height
    dna_strings = variants_df.loc[:, ('ref', 'alt')]
    dna_string_lens = dna_strings.map(lambda x: len(x))
    max_dna_string_len = dna_string_lens.max(axis=None)
    rowHeights = ceil(max_dna_string_len / 5) * 12
    rowHeights = 36 if rowHeights < 36 else rowHeights
    # Sort by "ACMG_classification"
    ACMG_classification_values = ['Патогенный', 'Вероятно патогенный', 'Вариант неясного значения', 'Вероятно доброкачественный',
                                  'Доброкачественный']
    variants_df['ACMG_classification'] = pd.Categorical(variants_df['ACMG_classification'], ACMG_classification_values)
    variants_df.sort_values(['ACMG_classification', 'chrom', 'pos_GRCh38'], inplace=True)
    # Create table style to color table cells
    Table_Style_colors = color_table_cells(variants_df)
    # Turn all values in the table into strings
    VariantsDF_colnames = list(variants_df.columns)
    VariantsDF_colnames.remove('PopFreq_GNOMAD_v3.1.2')
    VariantsDF_dtypes = {colname: 'str' for colname in VariantsDF_colnames}
    variants_df = variants_df.astype(VariantsDF_dtypes)
    # Tune "exon/intron" column values display
    variants_df['exon/intron'] = variants_df['exon/intron'].map(lambda x: insert_br_to_ExonOrIntron(x))
    # Tune "HGVS_VariantName" column values display
    variants_df['HGVS_VariantName'] = variants_df['HGVS_VariantName'].map(lambda x: ama_3letter_to_1letter(x))
    variants_df['HGVS_VariantName'] = variants_df['HGVS_VariantName'].map(lambda x: insert_br_to_hgvs(x))
    # Tune "PopFreq_GNOMAD_v3.1.2" column values display
    variants_df['PopFreq_GNOMAD_v3.1.2'] = variants_df['PopFreq_GNOMAD_v3.1.2'].map(lambda x: round_gnomad(x))
    # Tune "ACMG_classification" column values display
    variants_df['ACMG_classification'] = variants_df['ACMG_classification'].map(lambda x: insert_br_to_ACMG(x))
    # Convert all table values into Paragraph
    variants_df = variants_df.map(lambda x: Paragraph(x, table_style))
    # Create new header for the table
    variants_new_header = ['Хромосома', 'Позиция<br/>(hg38)', 'Реф.<br/>аллель', 'Обн.<br/>аллель', 'Ген', 'Тип варианта', 'Транскрипт',
                           'Экзон/<br/>интрон', 'Наименование<br/>варианта', 'Глубина<br/>прочтения', 'Генотип',
                           'Популяционная<br/>частота<br/>(gnomAD v.3.1.2)', 'Классификация<br/>варианта по ACMG']
    variants_new_header = [Paragraph(colname, table_style) for colname in variants_new_header]
    # Convert table to the list to create Table object
    variants_list = variants_df.values.tolist()
    variants_list.insert(0, variants_new_header)
    # Make Table object and apply style
    colWidths = [51, 45, 34, 34, 32, 74, 60, 40, 82, 50, 60, 72, 92]
    table = Table(variants_list, repeatRows=1, colWidths=colWidths, rowHeights=rowHeights) # repeatRows=1 makes the header repeat
    # Coordinates for TableStyle are (column, row); 0-indexed; ranges are inclusive; (-1, -1) means last column, last row.
    Table_Style_sizes = [("GRID", (0, 0), (-1, -1), 0.9, colors.black),
                         ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                         ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                         ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
                         ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
                         ("TOPPADDING", (0, 0), (-1, -1), 1),
                         ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]
    Table_Style = Table_Style_sizes + Table_Style_colors
    table.setStyle(TableStyle(Table_Style))
    return table
# DEF make_Platypus_table -------------------------------------------------------------------------------------------------------------

class ConditionalSpacer(Flowable):
    """
    A custom flowable that inserts either a Spacer or PageBreak
    based on available space on the current page.
    """
    def __init__(self, spacer_height=None, threshold=None):
        """
        Args:
            spacer_height: Height of spacer to use if there's enough room
            threshold: Minimum space needed on page (beyond text height) to avoid page break
        """
        Flowable.__init__(self)
        self.spacer_height = spacer_height
        self.threshold = threshold
        self.width = 0
        self.height = 0
    def wrap(self, availWidth, availHeight):
        """
        Determine what spacing to use based on available height.
        Returns the dimensions this flowable will consume.
        """
        if availHeight >= self.threshold:
            # Enough space for text block - use spacer
            self.height = self.spacer_height
            self.use_page_break = False
        else:
            # Not enough space - force page break
            self.height = availHeight  # Consume remaining space to force break
            self.use_page_break = True
        return (0, self.height)
    def draw(self):
        """
        Draw method - nothing to actually draw, spacing is handled by wrap()
        """
        pass

def write_info_and_table(variants_df, AnalysisInfo_lst, report_filepath):
    # Define features
    ## Document size
    page_width, page_height = landscape(A4)
    ## Document font
    font_filepath = _find_segoeui_font()
    font_name = "SegoeUI"
    ## Document body margins
    table_TopMargin = 101
    bottomMargin = 47
    doc_sideMargin = 52
    ## Table Paragraph style
    table_fontSize = 9
    ## Info Paragraph style
    info_fontSize = 10
    info_leading = 14
    ## Space between table and info
    spacer_height = 30
    min_space_required = spacer_height + info_fontSize + info_leading * 6 + bottomMargin
    #
    # Write document body (table and info)
    ## Create document
    doc = SimpleDocTemplate(report_filepath, pagesize=(page_width, page_height),
                            topMargin=table_TopMargin, bottomMargin=bottomMargin,
                            leftMargin=doc_sideMargin, rightMargin=doc_sideMargin)
    ##
    ## Create styles
    pdfmetrics.registerFont(TTFont(font_name, font_filepath))
    table_style = ParagraphStyle(name="TableStyle", fontName="SegoeUI", fontSize=table_fontSize, alignment=TA_CENTER, wordWrap='CJK')
    info_style = ParagraphStyle(name="InfoStyle", fontName="SegoeUI", fontSize=info_fontSize, leading=info_leading)
    ##
    ## Create table and append to the report
    table = make_Platypus_table(variants_df, table_style)
    report = [table]
    ##
    ## Append info lines to the report
    ### Add space between the end of the table and the first line of info
    report.append(ConditionalSpacer(spacer_height=spacer_height, threshold=min_space_required))
    ### Add info lines
    AnalysisInfo_lst = [Paragraph(line, info_style) for line in AnalysisInfo_lst]
    AnalysisInfo_lst = KeepTogether(AnalysisInfo_lst)
    report += [AnalysisInfo_lst]
    ##
    ## Build PDF
    doc.build(report)
# DEF write_info_and_table ------------------------------------------------------------------------------------------------------------




def write_resequencing_notice(report_filepath):
    # Define features
    ## Document size
    page_width, page_height = landscape(A4)
    ## Document font
    font_filepath = _find_segoeui_font()
    font_name = "SegoeUI"
    ## Document body margins
    table_TopMargin = 101
    bottomMargin = 47
    doc_sideMargin = 52
    ## Info Paragraph style
    info_fontSize = 10
    info_leading = 14
    #
    # Write document body (table and info)
    ## Create document
    doc = SimpleDocTemplate(report_filepath, pagesize=(page_width, page_height),
                            topMargin=table_TopMargin, bottomMargin=bottomMargin,
                            leftMargin=doc_sideMargin, rightMargin=doc_sideMargin)
    ##
    ## Create styles
    pdfmetrics.registerFont(TTFont(font_name, font_filepath))
    info_style = ParagraphStyle(name="InfoStyle", fontName="SegoeUI", fontSize=info_fontSize, leading=info_leading)
    ##
    ##
    ## Append info lines to the report
    resequencing_notice = 'Полученные результаты секвенирования не позволяют достоверно оценить наличие или отсутствие патогерных и вероятно патогенных генетических вариантов. Необходимо выполнить повторное секвенирование образца.'
    report = [Paragraph(resequencing_notice, info_style)]
    ##
    ## Build PDF
    doc.build(report)




def write_header_and_logo(report_filepath, logo_filepath, header_lst):
    # Define features
    page_width, page_height = landscape(A4)
    font_name = "SegoeUI"
    ## Header and page number margins
    header_sideMargin = 57
    header_topMargin = 47
    PageNum_bottomMargin = 32
    PageNum_sideMargin = page_width - header_sideMargin
    ## Header and page number font features
    header_fontSize = 11
    HeaderLine_VerticalSpace = 24
    PageNum_fontSize = 10
    ## Logo size and coordinates
    logo_width, logo_height = 145, 45.5
    logo_x = page_width - logo_width - header_sideMargin
    logo_y = page_height - logo_height - header_topMargin + header_fontSize
    #
    # Write header and page numbers to the document
    ## Load logo
    logo_xobj = pagexobj(pdfrw_PdfReader(logo_filepath).pages[0])
    ### Get original size of the PDF form
    orig_logo_width = logo_xobj.BBox[2] - logo_xobj.BBox[0]
    orig_logo_height = logo_xobj.BBox[3] - logo_xobj.BBox[1]
    ### Calculate scale ratios
    logo_scale_x = logo_width / orig_logo_width
    logo_scale_y = logo_height / orig_logo_height
    ##
    ## Write header and page number to the overlay PDF
    reader = PdfReader(report_filepath)
    writer = PdfWriter()
    page_num = len(reader.pages)
    overlay_pdf = []
    for page_i in range(page_num):
        ### Create canvas
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=landscape(A4))
        ### Draw the logo
        #### Register the form XObject
        logo_FormName = makerl(c, logo_xobj)
        c.saveState()
        c.translate(logo_x, logo_y)
        c.scale(logo_scale_x, logo_scale_y)
        c.doForm(logo_FormName)
        c.restoreState()
        ### Write header
        c.setFont(font_name, header_fontSize)
        HeaderLine_y = page_height - header_topMargin
        for header_line in header_lst:
            c.drawString(header_sideMargin, HeaderLine_y, header_line)
            HeaderLine_y -= HeaderLine_VerticalSpace
        ### Write page number
        c.setFont(font_name, PageNum_fontSize)
        page_num_txt = f"Лист {page_i + 1} из {page_num}"
        c.drawRightString(PageNum_sideMargin, PageNum_bottomMargin, page_num_txt)
        ### Save overlay
        c.save()
        packet.seek(0)
        overlay_pdf.append(PdfReader(packet))
    ##
    ## Overlay page with table and pages with header
    for page_i in range(page_num):
        original_page = reader.pages[page_i]
        overlay_page = overlay_pdf[page_i].pages[0]
        original_page.merge_page(overlay_page)
        writer.add_page(original_page)
    ##
    ## Write final PDF
    with open(report_filepath, "wb") as handle:
        writer.write(handle)
