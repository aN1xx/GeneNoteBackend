# IMPORT MODULES------------------------------------------------------------------------------------------------------------------------------------
from sys import argv as sargv
import pandas as pd
import re
# IMPORT MODULES------------------------------------------------------------------------------------------------------------------------------------




# DEFINE FUNCTIONS----------------------------------------------------------------------------------------------------------------------------------
def import_DepthByBase(DepthByBase_filepath):
    colnames = ['chrom', 'pos_GRCh38', 'depth']
    dtypes = ['str', 'int', 'int']
    dtypes = {colname: dtype for colname, dtype in zip(colnames, dtypes)}
    DepthByBase_df = pd.read_csv(DepthByBase_filepath, skiprows=1, sep='\t', names=colnames, dtype=dtypes)
    return DepthByBase_df


def import_vcf(vcf_filepath):
    colnames = ['chrom', 'pos', 'id', 'ref', 'alt', 'qual', 'filter', 'info', 'format', 'sample']
    dtypes = ['str', 'int', 'str', 'str', 'str', 'float', 'str', 'str', 'str', 'str']
    dtypes = {colname: dtype for colname, dtype in zip(colnames, dtypes)}
    vcf_handle = open(vcf_filepath, 'r')
    for line in vcf_handle:
        if '#CHROM' in line:
            break
    vcf_df = pd.read_csv(vcf_handle, sep='\t', names=colnames, dtype=dtypes)
    vcf_handle.close() 
    return vcf_df


# create_anchor_1row_summary_df function group --------------------
def create_1row_summary_df():
    colnames = ['chrom', 'pos_GRCh38', 'ref', 'alt', 'gene', 'transcript', 'exon/intron', 'HGVS_VariantName', 'genotype',
                'variant_caller', 'gatk_depth', 'gatk_allele_depth', 'gatk_allele_fraction',
                'artifact_db_num', 'is_variant', 'is_artifact']
    dtypes = ['str', 'Int64'] + 8 * ['str'] + 2 * ['Int64'] + ['Float64'] + ['Int64'] + 2 * ['str']
    dtypes = {colname: dtype for colname, dtype in zip(colnames, dtypes)}
    empty_row = [pd.NA] * len(colnames)
    summary_series = pd.Series(empty_row, index=colnames)
    summary_df = pd.DataFrame(summary_series)
    summary_df = summary_df.T
    summary_df = summary_df.astype(dtypes)
    return summary_df


def get_row_values(row):
    """
    row must be of pandas.Series type.
    """
    chrom = row['chrom']
    pos = row['pos']
    ref = row['ref']
    alt = row['alt']
    info = row['info']
    format_data = row['sample']
    return chrom, pos, ref, alt, info, format_data


def create_anchor_1row_summary_df(anchor_row, anchor_tool_dir):
    summary_df_1row = create_1row_summary_df()
    chrom, pos, ref, alt, info, format_data = get_row_values(anchor_row)
    ## FORMAT in GATK HaplotypeCaller VCF: GT:AD:AF:DP:GQ:PL
    ## GT - Genotype
    ## AD - Allelic depths for the ref and alt alleles in the order listed
    ## AF - Allele fractions of alternate alleles in the tumor
    ## DP - Approximate read depth (reads with MQ=255 or with bad mates are filtered)
    ## GQ - Genotype Quality
    ## Normalized, Phred-scaled likelihoods for genotypes as defined in the VCF specification
    genotype, AD, AF, gatk_depth, GQ, PL = format_data.split(':')
    ## Get allele depth of the first alternative allele listed
    gatk_allele_depth = AD.split(',')[1]
    ## Get allele fraction of the first alternative allele listed
    gatk_allele_fraction = AF.split(',')[0]
    ##
    csq = re.search('CSQ=.+?(;|$)', info).group()
    csq = csq.replace('CSQ=', '')
    annots_per_transcript = csq.split(',')
    annots_MANE_transcript = [annots for annots in annots_per_transcript if (MANE_transcripts[0] in annots) or (MANE_transcripts[1] in annots)][0]
    gene, transcript, exon, intron, HGVSc, HGVSp = annots_MANE_transcript.split('|')
    # https://asia.ensembl.org/Homo_sapiens/Transcript/Summary?db=core;g=ENSG00000139618;r=13:32315508-32400268;t=ENST00000380152
    # https://asia.ensembl.org/Homo_sapiens/Transcript/Summary?db=core;g=ENSG00000012048;r=17:43044295-43170245;t=ENST00000357654
    transcript = 'NM_000059.4' if transcript == 'ENST00000380152' else 'NM_007294.4'
    #
    if exon != '':
        exon_or_intron = f'экзон {exon.split('/')[0]}'
    else:
        exon_or_intron = f'интрон {intron.split('/')[0]}'
    #
    HGVSc = HGVSc.split(':')[-1]
    if HGVSp != '':
        HGVSp = HGVSp.split(':')[-1]
        HGVSp = HGVSp.replace('%3D', '=')
        HGVS = f'{HGVSc}({HGVSp})'
    else:
        HGVS = HGVSc
    ##
    summary_df_1row.loc[0, 'chrom'] = chrom
    summary_df_1row.loc[0, 'pos_GRCh38'] = pos
    summary_df_1row.loc[0, 'ref'] = ref
    summary_df_1row.loc[0, 'alt'] = alt
    summary_df_1row.loc[0, 'gene'] = gene
    summary_df_1row.loc[0, 'transcript'] = transcript
    summary_df_1row.loc[0, 'exon/intron'] = exon_or_intron
    summary_df_1row.loc[0, 'HGVS_VariantName'] = HGVS
    summary_df_1row.loc[0, 'genotype'] = 'гомозигота' if genotype == '1/1' else 'гетерозигота'
    summary_df_1row.loc[0, 'variant_caller'] = anchor_tool_dir
    summary_df_1row.loc[0, 'gatk_depth'] = int(gatk_depth)
    summary_df_1row.loc[0, 'gatk_allele_depth'] = int(gatk_allele_depth)
    summary_df_1row.loc[0, 'gatk_allele_fraction'] = float(gatk_allele_fraction)
    return summary_df_1row
# create_anchor_1row_summary_df function group --------------------


def update_1row_summary_df(tool_dir, summary_df_1row):
    summary_df_1row.loc[0, 'variant_caller'] = f'{summary_df_1row.loc[0, 'variant_caller']},{tool_dir}'
    return summary_df_1row


def FillNA_annotated_summary_df(annotated_summary_df):
    columns_to_fill = ['variant_db_num', 'variant_db_hetero_num', 'variant_db_homo_num', 'artifact_db_num']
    for column in columns_to_fill:
        annotated_summary_df[column] = annotated_summary_df[column].fillna(0)
    return annotated_summary_df
# DEFINE FUNCTIONS----------------------------------------------------------------------------------------------------------------------------------




# IMPORT ARGUMENTS----------------------------------------------------------------------------------------------------------------------------------
gatk_vcf_filepath = sargv[1]
ngsep_vcf_filepath = sargv[2]
xatlas_vcf_filepath = sargv[3]
DepthByBase_filepath = sargv[4]
GermlineVariants_DataBase_filepath = sargv[5]
GermlineArtifacts_DataBase_filepath = sargv[6]
VariantTable_filepath = sargv[7]
CovWidthAtDepths_filepath = sargv[8]
# IMPORT ARGUMENTS----------------------------------------------------------------------------------------------------------------------------------




# IMPORT VARIANT DATABASE---------------------------------------------------------------------------------------------------------------------------
GermlineVariants_DataBase_usecols = ['chrom', 'pos_GRCh38', 'ref', 'alt', 'variant_type', 'hetero_num', 'homo_num', 'PopFreq_GNOMAD_v3.1.2', 'ACMG_classification']
GermlineVariants_DataBase_df = pd.read_csv(GermlineVariants_DataBase_filepath, sep='\t', usecols=GermlineVariants_DataBase_usecols)
dtypes = ['str', 'Int64', 'str', 'str', 'str', 'Int64', 'Int64', 'Float64', 'str']
dtypes = {colname: dtype for colname, dtype in zip(GermlineVariants_DataBase_usecols, dtypes)}
GermlineVariants_DataBase_df = GermlineVariants_DataBase_df.astype(dtypes)
GermlineVariants_DataBase_df = GermlineVariants_DataBase_df.rename(columns={'hetero_num': 'variant_db_hetero_num', 'homo_num': 'variant_db_homo_num'})
# IMPORT VARIANT DATABASE---------------------------------------------------------------------------------------------------------------------------




# MAKE AND WRITE VARIANT TABLE----------------------------------------------------------------------------------------------------------------------
annotated_summary_colnames = ['chrom', 'pos_GRCh38', 'ref', 'alt', 'gene', 'variant_type', 'transcript', 'exon/intron', 'HGVS_VariantName',
                              'depth', 'genotype', 'PopFreq_GNOMAD_v3.1.2', 'ACMG_classification', 'variant_caller', 'gatk_depth',
                              'gatk_allele_depth', 'gatk_allele_fraction', 'variant_db_num', 'variant_db_hetero_num', 'variant_db_homo_num',
                              'artifact_db_num', 'is_variant', 'is_artifact']
#
tools = ['gatk', 'ngsep', 'xatlas']
MANE_transcripts = ['ENST00000357654', 'ENST00000380152']
#
vcf_dfs_dict = {}
vcf_dfs_dict['gatk'] = import_vcf(gatk_vcf_filepath)
vcf_dfs_dict['ngsep'] = import_vcf(ngsep_vcf_filepath)
vcf_dfs_dict['xatlas'] = import_vcf(xatlas_vcf_filepath)



summary_df = create_1row_summary_df()
#
suppl_tool_ind = 1
for anchor_tool in tools[:1]:
    anchor_vcf_df = vcf_dfs_dict[anchor_tool]
    #
    for i in range(anchor_vcf_df.shape[0]):
        anchor_row = anchor_vcf_df.iloc[i, :]
        chrom, pos, ref, alt, info, format_data = get_row_values(anchor_row)
        summary_1row_df = create_anchor_1row_summary_df(anchor_row, anchor_tool)
        #
        for tool in tools[suppl_tool_ind:]:
            vcf_df = vcf_dfs_dict[tool]
            row_df = vcf_df[(vcf_df['chrom'] == chrom) & (vcf_df['pos'] == pos) & (vcf_df['ref'] == ref) & (vcf_df['alt'] == alt)]
            if row_df.shape[0] > 0:
                if row_df.shape[0] > 1:
                    print(i, tool)
                row = row_df.squeeze(axis=0)
                summary_1row_df = update_1row_summary_df(tool, summary_1row_df)
                #
                row_ind = row_df.index
                vcf_dfs_dict[tool].drop(index=row_ind, inplace=True)
        #
        summary_df = pd.concat([summary_df, summary_1row_df])
    #
    suppl_tool_ind += 1
#
summary_df = summary_df.iloc[1:, :]
#
DepthByBase_df = import_DepthByBase(DepthByBase_filepath)
summary_df = summary_df.merge(DepthByBase_df, how='left', on=('chrom', 'pos_GRCh38'))
# summary_df = summary_df.loc[:, list(summary_df.columns[:9]) + ['depth'] + list(summary_df.columns[9:-1])]
#
annotated_summary_df = summary_df.merge(GermlineVariants_DataBase_df, how='left', on=['chrom', 'pos_GRCh38', 'ref', 'alt'])
annotated_summary_df['variant_db_num'] = annotated_summary_df['variant_db_hetero_num'] + annotated_summary_df['variant_db_homo_num']
annotated_summary_df = annotated_summary_df.loc[:, annotated_summary_colnames]
# MAKE AND WRITE VARIANT TABLE----------------------------------------------------------------------------------------------------------------------




# CHECK FOR ARTIFACTS-------------------------------------------------------------------------------------------------------------------------------
artifacts_df = pd.read_csv(GermlineArtifacts_DataBase_filepath, sep='\t')
colnames = list(artifacts_df.columns)
dtypes = ['str', 'str', 'int', 'str', 'str', 'int', 'int']
artifacts_dtypes = {colname: dtype for colname, dtype in zip(colnames, dtypes)}
artifacts_df = artifacts_df.astype(artifacts_dtypes)

for row_i in range(artifacts_df.shape[0]):
    artifact_row = artifacts_df.loc[row_i, :]
    chrom = artifact_row['chrom']
    pos = artifact_row['pos_GRCh38']
    ref = artifact_row['ref']
    alt = artifact_row['alt']
    artifact_variant_df = annotated_summary_df[(annotated_summary_df['chrom'] == chrom) &
                                                (annotated_summary_df['pos_GRCh38'] == pos) &
                                                (annotated_summary_df['ref'] == ref) &
                                                (annotated_summary_df['alt'] == alt)]
    if artifact_variant_df.shape[0] != 0:
        artifact_variant_i = list(artifact_variant_df.index)[0]
        occurrence_num = artifact_row['occurrence_num']
        annotated_summary_df.loc[artifact_variant_i, 'artifact_db_num'] = occurrence_num

annotated_summary_df = FillNA_annotated_summary_df(annotated_summary_df)

annotated_summary_df.to_csv(VariantTable_filepath, sep='\t', index=False)
# CHECK FOR ARTIFACTS-------------------------------------------------------------------------------------------------------------------------------




# CALCULATE COVERAGE WIDTH AT DEPTHS----------------------------------------------------------------------------------------------------------------
cov_width = DepthByBase_df.shape[0]
cov_width_at_depths = {}
for depth in [0, 5, 30, 50, 100]:
    cov_width_at_depth = DepthByBase_df[DepthByBase_df['depth'] > depth].shape[0]
    cov_width_at_depths[f'{depth}x_depth'] = [round((cov_width_at_depth / cov_width) * 100, 2)]
cov_width_at_depths_df = pd.DataFrame(cov_width_at_depths)
cov_width_at_depths_df.to_csv(CovWidthAtDepths_filepath, sep='\t', index=False)
# CALCULATE COVERAGE WIDTH AT DEPTHS----------------------------------------------------------------------------------------------------------------

