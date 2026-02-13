PipelineConfig_filepath="./pipeline_config.yaml" # Do not modify
Pipeline_filepath="./pipeline.py" # Do not modify
PipelineLog_filepath="../results/pipeline.log" # Modify

PipelineLog_dirpath=${PipelineLog_filepath%/*}
mkdir -p $PipelineLog_dirpath

snakemake \
--default-resources mem_mb=30 \
--printshellcmds \
--use-conda \
--configfile $PipelineConfig_filepath \
-s $Pipeline_filepath \
> $PipelineLog_filepath 2>&1
