##### IMPORT LIBRARIES #####
from sys import argv
import datetime
from os import makedirs
import pandas as pd




##### IMPORT COMMAND-LINE ARGIMENTS #####
vcf_prefix = argv[1]
combined_vcf_filepath = argv[2]




##### DEFINING INPUT #####
snp_vcf_filepath = f'{vcf_prefix}_snp.vcf'
indel_vcf_filepath = f'{vcf_prefix}_indel.vcf'




##### COMBINING VCFS #####
print(f"[{datetime.datetime.now()}] Creating universal VCF header.\n")
###
universal_vcf_header_block = ['##FILTER=<ID=low_qual,Description="Variant logistic regression P-value is less than 0.5">\n',
                              '##FILTER=<ID=low_VariantReads,Description="Variant read depth is less than 2"\n',
                              '##FILTER=<ID=SNPlowVariantRatio,Description="SNP read ratio is less than PL cutoff">\n',
                              '##FILTER=<ID=IndelLowVariantRatio,Description="Indel read ratio is less than 0.06">\n',
                              '##FILTER=<ID=SNPlowCoverage,Description="Total coverage is less than 6">\n',
                              '##FILTER=<ID=IndelLowCoverage,Description="Total coverage is less than 5">\n',
                              '##FILTER=<ID=high_coverage,Description="Total coverage is greater than 8000">\n',
                              '##FILTER=<ID=SNPsingleStrand,Description="All SNP reads are in a single strand direction">\n',
                              '##FILTER=<ID=IndelReadEndRatio,Description="Ratio of indel reads within 5 bp of read end is greater than 0.80">\n',
                              '##FILTER=<ID=No_data,Description="No valid reads on this site">\n',
                              '##FILTER=<ID=No_var,Description="No valid variants reads on this site">\n',
                              '##INFO=<ID=P,Number=1,Type=Float,Description="Variant p-value">\n',
                              '##INFO=<ID=equal_majority,Number=0,Type=Flag,Description="The called SNP has an equal number of reads indicating another variant call and base was chosen by highest summed quality score">\n']
###
snp_vcf_handle = open(snp_vcf_filepath, 'r')
combined_vcf_handle = open(combined_vcf_filepath, 'w')
vcf_header_last_line_beginning = '#CHROM'
for i, line in enumerate(snp_vcf_handle):
    if vcf_header_last_line_beginning in line:
        combined_vcf_handle.write(line)
        break
    elif i == 12:
        combined_vcf_handle.writelines(universal_vcf_header_block)
    elif i < 12 or i > 21:
        combined_vcf_handle.write(line)
###
indel_vcf_header_line_num = i


print(f"\n[{datetime.datetime.now()}] Importing and deduplicating VCFs.\n")
def deduplicate_vcf_df(vcf_df):
    vcf_df = vcf_df[~vcf_df['sample'].str.contains('0/0')].copy()
    #vcf_df.sort_values(by=['chrom', 'pos', 'qual', 'info'], ascending=True, inplace=True)
    #vcf_df.drop_duplicates(subset=['chrom', 'pos', 'ref', 'alt'], keep='last', ignore_index=True, inplace=True)
    return vcf_df
###
vcf_colnames = ['chrom', 'pos', 'id', 'ref', 'alt', 'qual', 'filter', 'info', 'format', 'sample']
vcf_dtype = {'chrom': 'str', 'pos': 'int', 'id': 'str', 'ref': 'str', 'alt': 'str',
             'qual': 'float', 'filter': 'str', 'info': 'str', 'format': 'str', 'sample': 'str'}
###
snp_vcf_df = pd.read_csv(snp_vcf_handle, sep='\t', names=vcf_colnames, dtype=vcf_dtype)
snp_vcf_handle.close()
indel_vcf_df = pd.read_csv(indel_vcf_filepath, skiprows=indel_vcf_header_line_num, sep='\t', names=vcf_colnames, dtype=vcf_dtype)
###
snp_vcf_df = deduplicate_vcf_df(snp_vcf_df)
indel_vcf_df = deduplicate_vcf_df(indel_vcf_df)


print(f"\n[{datetime.datetime.now()}] Preparing VCFs for combination.\n")
snp_filter_pairs = {'low_snpqual': 'low_qual', 'low_VariantRatio': 'SNPlowVariantRatio', 'low_coverage': 'SNPlowCoverage', 'single_strand': 'SNPsingleStrand'}
indel_filter_pairs = {'low_VariantRatio': 'IndelLowVariantRatio', 'low_coverage': 'IndelLowCoverage', 'read_end_ratio': 'IndelReadEndRatio'}
###
for old_flag, new_flag in snp_filter_pairs.items():
        snp_vcf_df.loc[:, 'filter'] = snp_vcf_df.iloc[:, 6].str.replace(old_flag, new_flag)
###
for old_flag, new_flag in indel_filter_pairs.items():
    indel_vcf_df.loc[:, 'filter'] = indel_vcf_df.iloc[:, 6].str.replace(old_flag, new_flag)


print(f"\n[{datetime.datetime.now()}] Combining VCFs.\n")
combined_vcf_df = pd.concat([snp_vcf_df, indel_vcf_df], ignore_index=True)
combined_vcf_df.sort_values(by=['chrom', 'pos'], inplace=True)


print(f"\n[{datetime.datetime.now()}] Writing combined VCF.\n")
combined_vcf_df.to_csv(combined_vcf_handle, sep='\t', index=False, header=False)
combined_vcf_handle.close()


print(f"\n[{datetime.datetime.now()}] Done.")

