# SET UP ==========================================================================================================================================================
import argparse
from os import listdir, makedirs
import pandas as pd
import Functions_MakeReport as rp
import Functions_UpdateDataBases as updb
import re
# SET UP ==========================================================================================================================================================




# CLI ============================================================================================================================================================
argparser = argparse.ArgumentParser(prog='Update data bases and make reports',
                                    description='Update Variants data base, Artifacts data base, and Patients data base, make reports.')
# Data bases
argparser.add_argument('--variants_db', help='Path to Variants data base.')
argparser.add_argument('--artifacts_db', help='Path to Artifacts data base.')
argparser.add_argument('--patients_db', help='Path to Patients data base.')
# Results
argparser.add_argument('--results', help='Path to "basic" results directory.')
# Report info
argparser.add_argument('--logo', help='Path to PDF logo for report.')

args = argparser.parse_args()
# CLI ============================================================================================================================================================




# INPUT ===========================================================================================================================================================
# Data bases
AnnotVar_filepath = args.variants_db
artifacts_filepath = args.artifacts_db
patients_filepath = args.patients_db
# Annotated variant tables
results_base_dirpath = args.results
# Report info
logo_filepath = args.logo
# INPUT ===========================================================================================================================================================




# DATAFRAME PARAMETERS ============================================================================================================================================
variants_usecols = ['chrom', 'pos_GRCh38', 'ref', 'alt', 'gene', 'variant_type', 'transcript', 'exon/intron', 'HGVS_VariantName', 'depth', 'genotype',
                    'PopFreq_GNOMAD_v3.1.2', 'ACMG_classification', 'is_variant', 'is_artifact']
annotated_columns_to_drop = ['depth', 'is_variant', 'is_artifact']
artifact_columns_to_drop = ['depth', 'gene', 'variant_type', 'transcript', 'exon/intron', 'HGVS_VariantName', 'PopFreq_GNOMAD_v3.1.2', 'ACMG_classification',
                            'is_variant', 'is_artifact']
# DATAFRAME PARAMETERS ============================================================================================================================================




# IMPORT DATA BASES ===============================================================================================================================================
annotated_df = pd.read_csv(AnnotVar_filepath, sep='\t', dtype={'chrom': 'str', 'freq': 'Float64', 'sample_num': 'Int64'})
artifacts_df = pd.read_csv(artifacts_filepath, sep='\t', dtype={'chrom': 'str', 'sample_num': 'Int64'})
patients_df = pd.read_csv(patients_filepath, sep='\t', dtype={'request_id': 'str', 'analysis_date': 'str'})
# IMPORT DATA BASES ===============================================================================================================================================




# UPDATE DATA BASES, MAKE AND WRITE REPORTS =======================================================================================================================
dir_contents = listdir(results_base_dirpath)
SampleDir_repattern = re.compile(r'[0-9]+(?:\.[0-9]+)?')
sample_dirs = []
for content in dir_contents:
    match_result = SampleDir_repattern.match(content)
    if match_result != None:
        sample_dir = match_result.group(0)
        sample_dirs.append(sample_dir)


#for variants_file in variants_files:
for sample_dir in sample_dirs:
    results_dirpath = f'{results_base_dirpath}/{sample_dir}'
    # UPDATE DATA BASES ----------------------------------------------------------------------------------
    sample = sample_dir
    variants_filepath = f'{results_dirpath}/variant_tables/{sample}_variants_annotated.tsv'
    variants_df = pd.read_csv(variants_filepath, sep='\t', usecols=variants_usecols, dtype={'chrom': 'str'})
    variants_df = variants_df.astype({'is_variant': 'bool', 'is_artifact': 'bool'}) # Crutch!
    #
    annotated_variants_df = variants_df[variants_df['is_variant']]
    # Update annotated variants database
    annotated_df = updb.update_db(annotated_variants_df, annotated_df, 'VariantName', annotated_columns_to_drop)
    # Update patients database
    patients_df = updb.update_patients_database(annotated_variants_df, sample, patients_df)
    # Update artifacts database
    artifact_variants_df = variants_df[variants_df['is_artifact']]
    artifacts_df = updb.update_db(artifact_variants_df, artifacts_df, 'ArtifactName', artifact_columns_to_drop)
    # UPDATE DATA BASES ----------------------------------------------------------------------------------
    #
    # MAKE REPORT ----------------------------------------------------------------------------------------
    annotated_variants_df = annotated_variants_df.drop(columns=['is_variant', 'is_artifact'])
    report_filepath = f'{results_dirpath}/variant_tables/{sample}_variants_report.pdf'
    if annotated_variants_df.shape[0] == 0:
        rp.write_resequencing_notice(report_filepath)
    else:
        PatientInfo_line, PatientAnalysis_line = rp.get_PatientInfo_PatientAnalysis_lines(sample, patients_df)
        #
        ReadStats_filepath = f'{results_dirpath}/trimming/{sample}_trimming_report.json'
        ReadStats_lst = rp.get_ReadStats_lst(ReadStats_filepath)
        #
        depth_filepath = f'{results_dirpath}/variant_tables/{sample}_CovWidthAtDepths.tsv'
        DepthAtCovPercent_lst = rp.get_DepthAtCovPercent_lst(depth_filepath)
        #
        header_lst = rp.make_header_lst(PatientInfo_line, PatientAnalysis_line)
        AnalysisInfo_lst = rp.make_AnalysisInfo_lst(ReadStats_lst, DepthAtCovPercent_lst)
        #
        rp.write_info_and_table(annotated_variants_df, AnalysisInfo_lst, report_filepath)
    rp.write_header_and_logo(report_filepath, logo_filepath, header_lst)
    # MAKE REPORT ----------------------------------------------------------------------------------------
# UPDATE DATA BASES, MAKE AND WRITE REPORTS =======================================================================================================================




# WRITE UPDATED DATA BASES ========================================================================================================================================
annotated_df.to_csv(AnnotVar_filepath, sep='\t', index=False)
artifacts_df.to_csv(artifacts_filepath, sep='\t', index=False)
patients_df.to_csv(patients_filepath, sep='\t', index=False)
# WRITE UPDATED DATA BASES ========================================================================================================================================
