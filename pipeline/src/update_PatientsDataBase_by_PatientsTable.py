# SET UP ==========================================================================================================================================================
import argparse
import pandas as pd
from datetime import datetime
from os import listdir, makedirs, remove, rename
# SET UP ==========================================================================================================================================================




# CLI ============================================================================================================================================================
argparser = argparse.ArgumentParser(prog='Update Patients data base, move FASTQ files',
                                    description='Update Patients data base, rename and move FASTQ files.')

argparser.add_argument('--patients_table', help='Path to Patients table.')
argparser.add_argument('--patients_db', help='Path to Patients data base.')

argparser.add_argument('--uploaded', help='Path to directory with uploaded FASTQ files.')
argparser.add_argument('--results', help='Path to directory to write pipeline results into.')

args = argparser.parse_args()
# CLI ============================================================================================================================================================




# INPUT ===========================================================================================================================================================
# Data bases
PatientsDB_filepath = args.patients_db
PatientsTable_filepath = args.patients_table
uploaded_dirpath = args.uploaded
results_dirpath = args.results
makedirs(results_dirpath, exist_ok=True)
# INPUT ===========================================================================================================================================================




# IMPORT PATIENTS DATA BASE AND TABLE =============================================================================================================================
PatientsTable_df = pd.read_csv(PatientsTable_filepath, sep='\t', dtype={'request_id': 'str'})
PatientsDB_df = pd.read_csv(PatientsDB_filepath, sep='\t', dtype={'request_id': 'str', 'analysis_date': 'str'})
# IMPORT DATA BASE AND TABLE ======================================================================================================================================




# DEFINE FUNCTIONS ================================================================================================================================================
def compute_RequestID_postfix(db_RequestIDs):
    db_RequestID_postfixes = [int(RequestID.split('.')[-1]) for RequestID in db_RequestIDs if '.' in RequestID]
    if len(db_RequestID_postfixes) == 0:
        return 2
    latter_postfix = max(db_RequestID_postfixes)
    current_postfix = latter_postfix + 1
    return current_postfix


def make_DateTime_str():
    DateTime = datetime.now()
    year, month, day, hour, minute, second = DateTime.year, DateTime.month, DateTime.day, DateTime.hour, DateTime.minute, DateTime.second
    DateTime_str = f'{year}.{month}.{day} {hour}:{minute}:{second}'
    return DateTime_str
# DEFINE FUNCTIONS ================================================================================================================================================




# UPDATE PATIENTS DATA BASE WITH PATIENTS TABLE DATA ==============================================================================================================
samples_to_rename = [] # (old_name, new_name)

for i in range(PatientsTable_df.shape[0]):
    PatientsTable_row = PatientsTable_df.loc[i, :].copy()
    table_RequestID = PatientsTable_row['request_id']
    PatientsDB_entry_df = PatientsDB_df[PatientsDB_df.request_id.str.contains(table_RequestID)]
    if PatientsDB_entry_df.shape[0] != 0:
        db_RequestIDs = PatientsDB_entry_df.request_id.to_list()
        postfix = compute_RequestID_postfix(db_RequestIDs)
        new_table_RequestID = f'{table_RequestID.split('.')[0]}.{postfix}'
        PatientsTable_row['request_id'] = new_table_RequestID
        samples_to_rename.append((table_RequestID, new_table_RequestID))
    PatientsTable_row['analysis_date'] = make_DateTime_str()
    PatientsTable_row['variants'] = pd.NA
    PatientsTable_row_df = pd.DataFrame(PatientsTable_row).T
    PatientsDB_df = pd.concat([PatientsTable_row_df, PatientsDB_df], ignore_index=True)

PatientsDB_df.to_csv(PatientsDB_filepath, sep='\t', index=False)

remove(PatientsTable_filepath)
# UPDATE PATIENTS DATA BASE WITH PATIENTS TABLE DATA ==============================================================================================================




# RENAME AND MOVE FASTQ FILES =====================================================================================================================================
samples_to_rename.sort(key=lambda x: x[0])
SamplesToRename_df = pd.DataFrame(samples_to_rename, columns=['sample_name', 'new_sample_name'])

fastq_files = [file for file in listdir(uploaded_dirpath) if '.fastq.gz' in file]
fastq_files.sort()
FastqFiles_df = pd.DataFrame({'file': fastq_files})
FastqFiles_df['sample_name'] = FastqFiles_df.file.map(lambda x: x.split('_')[0])

FastqFiles_df = pd.merge(FastqFiles_df, SamplesToRename_df, how='outer', on='sample_name')

for i in range(FastqFiles_df.shape[0]):
    FastqFiles_row = FastqFiles_df.loc[i, :]
    file, sample_name, new_sample_name = FastqFiles_row['file'], FastqFiles_row['sample_name'], FastqFiles_row['new_sample_name']
    UploadedFastq_filepath = f'{uploaded_dirpath}/{file}'
    sample_dir = sample_name
    if FastqFiles_df['new_sample_name'].isna()[i] != True:
        file = file.replace(sample_name, new_sample_name)
        sample_dir = new_sample_name
    InputFastq_dirpath = f'{results_dirpath}/{sample_dir}/input'
    makedirs(InputFastq_dirpath, exist_ok=True)
    InputFastq_filepath = f'{InputFastq_dirpath}/{file}'
    rename(UploadedFastq_filepath, InputFastq_filepath)
# RENAME AND MOVE FASTQ FILES =====================================================================================================================================
