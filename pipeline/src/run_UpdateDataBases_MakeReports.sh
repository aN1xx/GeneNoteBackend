# Modify:
# --variants_tables
# --trim_stats
# --depths
# --reports

# Do not modify:
# --variants_db
# --artifacts_db
# --patients_db
# --logo

python3 UpdateDataBases_MakeReports.py \
--variants_db ../data_bases/GermlineVariants_DataBase.tsv \
--artifacts_db ../data_bases/GermlineArtifacts_DataBase.tsv \
--patients_db ../data_bases/Patients_DataBase.tsv \
--results ../results \
--logo ./olymp_logo.pdf
