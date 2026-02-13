# Modify:
# --patients_table
# --uploaded
# --input

# Do not modify:
# --patients_db

python3 ./update_PatientsDataBase_by_PatientsTable.py \
--patients_table ../uploaded/Patients_Table.tsv \
--patients_db ../data_bases/Patients_DataBase.tsv \
--uploaded ../uploaded \
--results ../results