# COMMON VARIABLES----------------------------------------------------------------------------------------------------------------------------------
## Directories
base_results_dirpath = config['base_results_dirpath']

# Single sample mode: use sample from config if provided
SAMPLE = config.get('sample', None)
if SAMPLE:
    # Single sample mode - use sample from config
    samples = [SAMPLE]
    numbers = ['1']  # Default S1
else:
    # Multi-sample mode - discover samples from filesystem
    (samples, numbers) = glob_wildcards(base_results_dirpath + '/*/input/{sample}_S{number}_L001_R1_001.fastq.gz')

## Files
genome_fasta_filepath = config['genome_fasta_filepath']
# COMMON VARIABLES----------------------------------------------------------------------------------------------------------------------------------


# FASTQ TRIMMING------------------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
# Use wildcard {sample} for paths - Snakemake will substitute it
results_dirpath = base_results_dirpath + '/{sample}'
fastq_trimming_dirpath = results_dirpath + '/trimming'


## RULE TRIM_FASTQ
### Input
raw_fastq_dirpath = results_dirpath + '/input'
def get_fastq(wildcards):
    sample = wildcards.sample
    raw_fastq1_filepath = base_results_dirpath + '/' + sample + '/input/' + sample + '_S{number}_L001_R1_001.fastq.gz'
    raw_fastq2_filepath = base_results_dirpath + '/' + sample + '/input/' + sample + '_S{number}_L001_R2_001.fastq.gz'
    globbed = glob_wildcards(raw_fastq1_filepath)
    raw_fastq1_filepath, raw_fastq2_filepath = expand([raw_fastq1_filepath, raw_fastq2_filepath], number=globbed.number)
    return {'raw_fastq1_filepath': raw_fastq1_filepath, 'raw_fastq2_filepath': raw_fastq2_filepath}
### Output
trimmed_fastq_prefix = fastq_trimming_dirpath + '/{sample}_trimmed'
trimmed_fastq1_filepath = trimmed_fastq_prefix + '_1.fastq.gz'
trimmed_fastq2_filepath = trimmed_fastq_prefix + '_2.fastq.gz'
unpaired_fastq_prefix = fastq_trimming_dirpath + '/{sample}_unpaired'
###
rule trim_fastq:
    input:
        unpack(get_fastq)
    output:
        trimmed_fastq1_filepath = trimmed_fastq1_filepath,
        trimmed_fastq2_filepath = trimmed_fastq2_filepath,
        unpaired_fastq1_filepath = unpaired_fastq_prefix + '_1.fastq.gz',
        unpaired_fastq2_filepath = unpaired_fastq_prefix + '_2.fastq.gz',
        failed_fastq_filepath = fastq_trimming_dirpath + '/{sample}_failed.fastq.gz',
        trimming_HTMLReport_filepath = fastq_trimming_dirpath + '/{sample}_trimming_report.html',
        trimming_JSONReport_filepath = fastq_trimming_dirpath + '/{sample}_trimming_report.json'
    log:
        fastq_trimming_dirpath + '/{sample}_trimming.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "fastp "
        "--thread 1 "
        # Input
        "--in1 {input.raw_fastq1_filepath} "
        "--in2 {input.raw_fastq2_filepath} "
        # Output
        "--out1 {output.trimmed_fastq1_filepath} "
        "--out2 {output.trimmed_fastq2_filepath} "
        "--unpaired1 {output.unpaired_fastq1_filepath} "
        "--unpaired2 {output.unpaired_fastq2_filepath} "
        "--failed_out {output.failed_fastq_filepath} "
        "--html {output.trimming_HTMLReport_filepath} "
        "--json {output.trimming_JSONReport_filepath} "
        # Adapter trimming
        "--detect_adapter_for_pe "
        # Quality trimming
        "--cut_tail "
        "--cut_window_size 6 "
        "--cut_mean_quality 15 "
        # Quality filtering
        "--qualified_quality_phred 15 "
        "--unqualified_percent_limit 40 "
        # Length filtering
        "--length_required 36 "
        # Log
        "2> {log}"
# FASTQ TRIMMING------------------------------------------------------------------------------------------------------------------------------------


# FASTQ MAPPING-------------------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
fastq_mapping_dirpath = results_dirpath + '/mapping'
fastq_mapping_log_dirpath = fastq_mapping_dirpath + '/logs'


## RULE MAP_FASTQ
from gzip import open as gzopen
import sys
def extract_read_group(wildcards, fastq_trimming_dirpath=fastq_trimming_dirpath):
    """Construct read group for BAM form FASTQ header"""
    sample = str(wildcards.sample)
    # Use string concatenation to avoid Snakemake preprocessing f-string braces
    trimmed_fastq1_filepath = base_results_dirpath + '/' + sample + '/trimming/' + sample + '_trimmed_1.fastq.gz'
    try:
        with gzopen(trimmed_fastq1_filepath, 'rt') as handle:
            record_header = handle.readline().strip()
        record_header = record_header.replace('@', '')
        instrument_info, library_info = record_header.split()
        instrument, run, flowcell, lane, tile, x_pos, y_pos = instrument_info.split(':')
        ID = flowcell + '.' + lane
        PU = ID + '.' + sample
    except (FileNotFoundError, ValueError):
        # During DAG building, file may not exist yet - use placeholder
        ID = 'FLOWCELL.1'
        PU = ID + '.' + sample
    SM = sample
    PL = 'ILLUMINA'
    LB = 'Quasar-BRCA1/2'
    # Build read group string with concatenation
    read_group = "'@RG\\tID:" + ID + "\\tPU:" + PU + "\\tSM:" + SM + "\\tPL:" + PL + "\\tLB:" + LB + "'"
    return read_group
###
raw_bam_filepath = fastq_mapping_dirpath + '/{sample}.bam'
###
rule map_fastq:
    input:
        trimmed_fastq1_filepath = trimmed_fastq1_filepath,
        trimmed_fastq2_filepath = trimmed_fastq2_filepath
    output:
        raw_bam_filepath = raw_bam_filepath
    params:
        genome_FASTAIndex_prefix = config['genome_FASTAIndex_prefix'],
        read_group = extract_read_group
    log:
        fastq_mapping_log_dirpath + '/{sample}_mapping.log'
    threads: 8
    resources: mem_mb=30
    shell:
        "( "
        "bwa mem -t 8 -Y -R {params.read_group} {params.genome_FASTAIndex_prefix} {input.trimmed_fastq1_filepath} {input.trimmed_fastq2_filepath} "
        "| "
        "samtools sort --threads 8 -O bam -l 9 -o {output.raw_bam_filepath} - "
        ") "
        "2> {log}"


## RULE CLIP_PRIMERS
PrimersClipped_bam_filepath = fastq_mapping_dirpath + '/{sample}_PrimersClipped.bam'
###
rule clip_primers:
    input:
        raw_bam_filepath = raw_bam_filepath,
        PrimerCoords_bed_filepath = config['PrimerCoords_bed_filepath'],
        genome_fasta_filepath = genome_fasta_filepath
    output:
        PrimersClipped_bam_filepath = PrimersClipped_bam_filepath
    log:
        fastq_mapping_log_dirpath + '/{sample}_PrimersClipping.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "( "
        "samtools ampliconclip --threads 1 --hard-clip --strand --tolerance 0 --clipped -b {input.PrimerCoords_bed_filepath} -u {input.raw_bam_filepath} "
        "| "
        "samtools view --threads 1 --with-header - "
        "| "
        "awk '/^@/ || $6 ~ /H/' "
        "| "
        "samtools view --threads 1 --bam --uncompressed - "
        "| "
        "samtools sort --threads 1 -n --output-fmt bam -u - "
        "| "
        "samtools fixmate --threads 1 -u - - "
        "| "
        "samtools sort --threads 1 --output-fmt bam -u - "
        "| "
        "samtools calmd --threads 1 -b - {input.genome_fasta_filepath} > {output.PrimersClipped_bam_filepath} "
        ") "
        "2> {log}"


## RULE FIX_FLAGS
FixedFlags_bam_filepath = fastq_mapping_dirpath + '/{sample}_PrimersClipped_FlagsFixed.bam'
###
rule fix_flags:
    input:
        PrimersClipped_bam_filepath = PrimersClipped_bam_filepath
    output:
        FixedFlags_bam_filepath = FixedFlags_bam_filepath
    params:
        FlagsFixing_script_filepath = config['FlagsFixing_script_filepath']
    log:
        fastq_mapping_log_dirpath + '/{sample}_FlagsFixing.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "python3 {params.FlagsFixing_script_filepath} "
        "{input.PrimersClipped_bam_filepath} "
        "{output.FixedFlags_bam_filepath} "
        "> {log} 2>&1"


## RULE FILTER_BAM
filtered_bam_filepath = fastq_mapping_dirpath + '/{sample}_PrimersClipped_FlagsFixed_filtered.bam'
###
rule filter_bam:
    input:
        FixedFlags_bam_filepath = FixedFlags_bam_filepath
    output:
        filtered_bam_filepath = filtered_bam_filepath
    log:
        fastq_mapping_log_dirpath + '/{sample}_filtering.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "gatk PrintReads "
        # Read filters:
        "--disable-tool-default-read-filters true "
        "--read-filter MappedReadFilter "
        "--read-filter NotSecondaryAlignmentReadFilter "
        "--read-filter NonZeroReferenceLengthAlignmentReadFilter "
        "--read-filter MappingQualityAvailableReadFilter "
        "--read-filter MappingQualityReadFilter "
        "--read-filter PassesVendorQualityCheckReadFilter "
        "--read-filter GoodCigarReadFilter "
        "--read-filter WellformedReadFilter "
        # Input:
        "--input {input.FixedFlags_bam_filepath} "
        # Output:
        "--output {output.filtered_bam_filepath} "
        "2> {log}"
# FASTQ MAPPING-------------------------------------------------------------------------------------------------------------------------------------


# VARIANT CALLING-----------------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
VariantCalling_dirpath = results_dirpath + '/variant_calling'
### Files
VariantCallingIntervals_filepath = config['VariantCallingIntervals_filepath']


# GATK VARIANT CALLING------------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
gatk_dirpath = VariantCalling_dirpath + '/gatk'
gatk_log_dirpath = gatk_dirpath + '/logs'
### Other
gatk_name = '{sample}_GATK'


## RULE GATK_CALL_VARIANTS
### Output
gatk_vcf_filepath = gatk_dirpath + '/' + gatk_name + '.vcf'
###
rule gatk_call_variants:
    input:
        genome_fasta_filepath = genome_fasta_filepath,
        filtered_bam_filepath = filtered_bam_filepath,
        VariantCallingIntervals_filepath = VariantCallingIntervals_filepath
    output:
        gatk_vcf_filepath = gatk_vcf_filepath
    log:
        gatk_log_dirpath + '/' + gatk_name + '_VariantCalling.log'
    threads: 8
    resources: mem_mb=30
    shell:
        "gatk --java-options '-Xmx4g' HaplotypeCaller "
        "--native-pair-hmm-threads 8 "
        "--disable-tool-default-annotations "
        "--annotation AlleleFraction "
        "--annotation BaseQuality "
        "--annotation BaseQualityRankSumTest "
        "--annotation DepthPerAlleleBySample "
        "--annotation DepthPerSampleHC "
        "--annotation MappingQuality "
        "--annotation MappingQualityRankSumTest "
        # Input:
        "--reference {input.genome_fasta_filepath} "
        "--input {input.filtered_bam_filepath} "
        "--intervals {input.VariantCallingIntervals_filepath} "
        # Output:
        "--output {output.gatk_vcf_filepath} "
        "2> {log}"


## RULE NORMALIZE_GATK_VCF
normalized_gatk_vcf_filepath = gatk_dirpath + '/' + gatk_name + '_normalized.vcf'
###
rule normalize_gatk_vcf:
    input:
        gatk_vcf_filepath = gatk_vcf_filepath,
        genome_fasta_filepath = genome_fasta_filepath
    output:
        normalized_gatk_vcf_filepath = normalized_gatk_vcf_filepath
    log:
        gatk_log_dirpath + '/' + gatk_name + '_normalization.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "vt normalize "
        "-o {output.normalized_gatk_vcf_filepath} "
        "-r {input.genome_fasta_filepath} "
        "{input.gatk_vcf_filepath} "
        "2> {log}"


## RULE ANNOTATE_GATK_VCF
### Output
VEPAnnotated_gatk_vcf_filepath = gatk_dirpath + '/' + gatk_name + '_normalized_VEPAnnotated.vcf'
###
# VEP mode configuration:
# - For ONLINE mode (no cache needed): use --database (slower, needs internet)
# - For OFFLINE mode (with cache): use --offline --cache --dir_cache
VEP_USE_CACHE = config.get('vep_use_cache', False)
###
rule vep_annotate_gatk_vcf:
    input:
        normalized_gatk_vcf_filepath = normalized_gatk_vcf_filepath,
        genome_fasta_filepath = genome_fasta_filepath
    output:
        VEPAnnotated_gatk_vcf_filepath = VEPAnnotated_gatk_vcf_filepath,
        VEPAnnotation_report_filepath = gatk_dirpath + '/' + gatk_name + '_VEPAnnotation_report.html'
    log:
        gatk_log_dirpath + '/' + gatk_name + '_VEPAnnotation.log'
    threads: 1
    resources: mem_mb=3
    params:
        vep_cache_dir = config.get('vep_cache_dir', '/app/vep_cache'),
        vep_mode = "--offline --cache --dir_cache " + config.get('vep_cache_dir', '/app/vep_cache') if VEP_USE_CACHE else "--database"
    shell:
        "vep "
        "--force_overwrite "
        "{params.vep_mode} "
        "--hgvs "
        "--vcf "
        "--fields 'SYMBOL,Feature,EXON,INTRON,HGVSc,HGVSp' "
        "--fasta {input.genome_fasta_filepath} "
        "--input_file {input.normalized_gatk_vcf_filepath} "
        "--output_file {output.VEPAnnotated_gatk_vcf_filepath} "
        "--stats_file {output.VEPAnnotation_report_filepath} "
        "2> {log}"
# GATK VARIANT CALLING------------------------------------------------------------------------------------------------------------------------------


# NGSEP VARIANT CALLING-----------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
ngsep_dirpath = VariantCalling_dirpath + '/ngsep'
ngsep_log_dirpath = ngsep_dirpath + '/logs'
### Other
ngsep_name = '{sample}_NGSEP'


## RULE NGSEP_CALL_VARIANTS
ngsep_vcf_filepath = ngsep_dirpath + '/' + ngsep_name + '.vcf'
###
rule ngsep_call_variants:
    input:
        genome_fasta_filepath = genome_fasta_filepath,
        filtered_bam_filepath = filtered_bam_filepath
    output:
        ngsep_vcf_filepath
    params:
        sample_id = '{sample}',
        ngsep_vcf_prefix = ngsep_dirpath + '/' + ngsep_name + ''
    log:
        ngsep_log_dirpath + '/' + ngsep_name + '_VariantCalling.log'
    threads: 1
    resources: mem_mb=4
    shell:
        "java -jar {config[ngsep_jar_filepath]} SingleSampleVariantsDetector "
        "-maxAlnsPerStartPos 50 "
        "-minSVQuality 10 "
        # Input:
        "-r {input.genome_fasta_filepath} "
        "-i {input.filtered_bam_filepath} "
        "-sampleId {params.sample_id} "
        # Output:
        "-o {params.ngsep_vcf_prefix} "
        "2> {log}"


## RULE INDEX_NGSEP_VCF
bgzipped_ngsep_vcf_filepath = ngsep_vcf_filepath + '.gz'
ngsep_VCFIndex_filepath = bgzipped_ngsep_vcf_filepath + '.tbi'
###
rule index_ngsep_vcf:
    input:
        ngsep_vcf_filepath = ngsep_vcf_filepath
    output:
        bgzipped_ngsep_vcf_filepath = bgzipped_ngsep_vcf_filepath,
        ngsep_VCFIndex_filepath = ngsep_VCFIndex_filepath
    log:
        ngsep_log_dirpath + '/' + ngsep_name + '_indexing.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "( "
        "bgzip {input.ngsep_vcf_filepath} "
        "&& "
        "tabix {output.bgzipped_ngsep_vcf_filepath} "
        ") "
        "2> {log}"


## RULE SELECT_INTERVALS_NGSEP_VCF
IntervalsSelected_ngsep_vcf_filepath = ngsep_dirpath + '/' + ngsep_name + '_IntervalsSelected.vcf'
###
rule select_intervals_ngsep_vcf:
    input:
        bgzipped_ngsep_vcf_filepath = bgzipped_ngsep_vcf_filepath,
        VariantCallingIntervals_filepath = VariantCallingIntervals_filepath,
        ngsep_VCFIndex_filepath = ngsep_VCFIndex_filepath
    output:
        IntervalsSelected_ngsep_vcf_filepath = IntervalsSelected_ngsep_vcf_filepath
    log:
        ngsep_log_dirpath + '/' + ngsep_name + '_IntervalsSelection.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "bcftools view "
        "--output-type v "
        "--output {output.IntervalsSelected_ngsep_vcf_filepath} "
        "--regions-file {input.VariantCallingIntervals_filepath} "
        "{input.bgzipped_ngsep_vcf_filepath} "
        "2> {log}"


## RULE NORMALIZE_NGSEP_VCF
normalized_ngsep_vcf_filepath = ngsep_dirpath + '/' + ngsep_name + '_IntervalsSelected_normalized.vcf'
###
rule normalize_ngsep_vcf:
    input:
        IntervalsSelected_ngsep_vcf_filepath = IntervalsSelected_ngsep_vcf_filepath,
        genome_fasta_filepath = genome_fasta_filepath
    output:
        normalized_ngsep_vcf_filepath = normalized_ngsep_vcf_filepath
    log:
        ngsep_log_dirpath + '/' + ngsep_name + '_normalization.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "vt normalize "
        "-o {output.normalized_ngsep_vcf_filepath} "
        "-r {input.genome_fasta_filepath} "
        "{input.IntervalsSelected_ngsep_vcf_filepath} "
        "2> {log}"
# NGSEP VARIANT CALLING-----------------------------------------------------------------------------------------------------------------------------


# XATLAS VARIANT CALLING----------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
xatlas_dirpath = VariantCalling_dirpath + '/xatlas'
xatlas_log_dirpath = xatlas_dirpath + '/logs'
### Other
xatlas_name = '{sample}_xAtlas'


## RULE XATLAS_CALL_VARIANTS
xatlas_vcf_prefix = xatlas_dirpath + '/' + xatlas_name + ''
xatlas_SnpVcf_filepath = xatlas_vcf_prefix + '_snp.vcf'
xatlas_IndelVcf_filepath = xatlas_vcf_prefix + '_indel.vcf'
###
rule xatlas_call_variants:
    input:
        genome_fasta_filepath = genome_fasta_filepath,
        filtered_bam_filepath = filtered_bam_filepath,
        genes_bed_filepath = config['genes_bed_filepath']
    output:
        xatlas_SnpVcf_filepath,
        xatlas_IndelVcf_filepath
    params:
        xatlas_vcf_prefix = xatlas_vcf_prefix,
        sample_id = '{sample}'
    log:
        xatlas_log_dirpath + '/' + xatlas_name + '_VariantCalling.log'
    threads: 8
    resources: mem_mb=30
    shell:
        "xatlas "
        "--multithread 8 "
        # Input:
        "--ref {input.genome_fasta_filepath} "
        "--in {input.filtered_bam_filepath} "
        "--capture-bed {input.genes_bed_filepath} "
        # Output:
        "--prefix {params.xatlas_vcf_prefix} "
        "--sample-name {params.sample_id} "
        "2> {log}"


## RULE MERGE_XATLAS_VCF
merged_xatlas_vcf_filepath = xatlas_dirpath + '/' + xatlas_name + '_merged.vcf'
###
rule merge_xatlas_vcf:
    input:
        xatlas_SnpVcf_filepath,
        xatlas_IndelVcf_filepath
    output:
        merged_xatlas_vcf_filepath = merged_xatlas_vcf_filepath
    params:
        xatlas_merging_script_filepath = config['xatlas_merging_script_filepath'],
        xatlas_vcf_prefix = xatlas_vcf_prefix
    log:
        xatlas_log_dirpath + '/' + xatlas_name + '_merging.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "python3 {params.xatlas_merging_script_filepath} "
        "{params.xatlas_vcf_prefix} "
        "{output.merged_xatlas_vcf_filepath} "
        "> {log} 2>&1"


# RULE BGZIP_XATLAS_VCF
bgzipped_xatlas_vcf_filepath = merged_xatlas_vcf_filepath + '.gz'
xatlas_VCFIndex_filepath = bgzipped_xatlas_vcf_filepath + '.tbi'
###
rule index_xatlas_vcf:
    input:
        merged_xatlas_vcf_filepath = merged_xatlas_vcf_filepath
    output:
        bgzipped_xatlas_vcf_filepath = bgzipped_xatlas_vcf_filepath,
        xatlas_VCFIndex_filepath = xatlas_VCFIndex_filepath
    log:
        xatlas_log_dirpath + '/' + xatlas_name + '_indexing.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "( "
        "bgzip {input.merged_xatlas_vcf_filepath} "
        "&& "
        "tabix {output.bgzipped_xatlas_vcf_filepath} "
        ") "
        "2> {log}"


# RULE SELECT_INTERVALS_XATLAS_VCF
IntervalsSelected_xatlas_vcf_filepath = xatlas_dirpath + '/' + xatlas_name + '_merged_IntervalsSelected.vcf'
###
rule select_intervals_xatlas_vcf:
    input:
        bgzipped_xatlas_vcf_filepath = bgzipped_xatlas_vcf_filepath,
        VariantCallingIntervals_filepath = VariantCallingIntervals_filepath,
        xatlas_VCFIndex_filepath = xatlas_VCFIndex_filepath
    output:
        IntervalsSelected_xatlas_vcf_filepath = IntervalsSelected_xatlas_vcf_filepath
    log:
        xatlas_log_dirpath + '/' + xatlas_name + '_IntervalsSelection.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "bcftools view "
        "--output-type v "
        "--output {output.IntervalsSelected_xatlas_vcf_filepath} "
        "--regions-file {input.VariantCallingIntervals_filepath} "
        "{input.bgzipped_xatlas_vcf_filepath} "
        "2> {log}"


# RULE NORMALIZE_XATLAS_VCF
normalized_xatlas_vcf_filepath = xatlas_dirpath + '/' + xatlas_name + '_merged_IntervalsSelected_normalized.vcf'
###
rule normalize_xatlas_vcf:
    input:
        IntervalsSelected_xatlas_vcf_filepath = IntervalsSelected_xatlas_vcf_filepath,
        genome_fasta_filepath = genome_fasta_filepath
    output:
        normalized_xatlas_vcf_filepath = normalized_xatlas_vcf_filepath
    log:
        xatlas_log_dirpath + '/' + xatlas_name + '_normalization.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "vt normalize "
        "-o {output.normalized_xatlas_vcf_filepath} "
        "-r {input.genome_fasta_filepath} "
        "{input.IntervalsSelected_xatlas_vcf_filepath} "
        "2> {log}"
# XATLAS VARIANT CALLING----------------------------------------------------------------------------------------------------------------------------
# VARIANT CALLING-----------------------------------------------------------------------------------------------------------------------------------


# VARIANT TABLE MAKING------------------------------------------------------------------------------------------------------------------------------
## COMMON VARIABLES
### Directories
VariantTableOuter_dirpath = results_dirpath + '/variant_tables'
VariantTable_log_dirpath = VariantTableOuter_dirpath + '/logs'


## RULE COMPUTE_DEPTH_BY_BASE
DepthByBase_filepath = VariantTableOuter_dirpath + '/{sample}_DepthByBase.bed'
###
rule compute_depth_by_base:
    input:
        filtered_bam_filepath = filtered_bam_filepath,
        VariantCallingIntervals_filepath = VariantCallingIntervals_filepath
    output:
        DepthByBase_filepath = DepthByBase_filepath
    log:
        VariantTable_log_dirpath + '/{sample}_DepthByBaseCalculation.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "samtools depth "
        "--threads 1 "
        "-a "
        "-b {input.VariantCallingIntervals_filepath} "
        "-H "
        "-o {output.DepthByBase_filepath} "
        "{input.filtered_bam_filepath} "
        "2> {log}"


# RULE MAKE_VARIANT_TABLE
VariantTable_filepath = VariantTableOuter_dirpath + '/{sample}_variants_raw.tsv'
CovWidthAtDepths_filepath = VariantTableOuter_dirpath + '/{sample}_CovWidthAtDepths.tsv'
###
rule make_variant_table:
    input:
        VEPAnnotated_gatk_vcf_filepath = VEPAnnotated_gatk_vcf_filepath,
        normalized_ngsep_vcf_filepath = normalized_ngsep_vcf_filepath,
        normalized_xatlas_vcf_filepath = normalized_xatlas_vcf_filepath,
        DepthByBase_filepath = DepthByBase_filepath,
        AnnotatedVariantDataBase_filepath = config['AnnotatedVariantDataBase_filepath'],
        ArtifactsDataBase_filepath = config['ArtifactsDataBase_filepath']
    output:
        VariantTable_filepath = VariantTable_filepath,
        CovWidthAtDepths_filepath = CovWidthAtDepths_filepath
    params:
        MakingVariantTable_script_filepath = config['MakingVariantTable_script_filepath']
    log:
        VariantTable_log_dirpath + '/{sample}_VariantTableMaking.log'
    threads: 1
    resources: mem_mb=3
    shell:
        "python3 {params.MakingVariantTable_script_filepath} "
        "{input.VEPAnnotated_gatk_vcf_filepath} "
        "{input.normalized_ngsep_vcf_filepath} "
        "{input.normalized_xatlas_vcf_filepath} "
        "{input.DepthByBase_filepath} "
        "{input.AnnotatedVariantDataBase_filepath} "
        "{input.ArtifactsDataBase_filepath} "
        "{output.VariantTable_filepath} "
        "{output.CovWidthAtDepths_filepath} "
        "> {log} 2>&1"
# VARIANT TABLE MAKING------------------------------------------------------------------------------------------------------------------------------


# RULE ALL------------------------------------------------------------------------------------------------------------------------------------------
###
rule all:
    input:
        expand(VariantTable_filepath, sample=samples),
        expand(CovWidthAtDepths_filepath, sample=samples)
    default_target: True
# RULE ALL------------------------------------------------------------------------------------------------------------------------------------------

