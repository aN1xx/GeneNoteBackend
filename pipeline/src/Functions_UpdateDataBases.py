import pandas as pd


# get_variant_info -----------------------
def get_variant_info(variant_row):
    chrom = variant_row['chrom']
    pos = variant_row['pos_GRCh38']
    ref = variant_row['ref']
    alt = variant_row['alt']
    genotype = variant_row['genotype']
    return chrom, pos, ref, alt, genotype
# get_variant_info ----------------------


# make_variant_name ------------------------------
def make_variant_name(chrom, pos, ref, alt):
    variant_name = f'chr{chrom}-{pos}-{ref}-{alt}'
    return variant_name
# make_variant_name ------------------------------


# update_db -------------------------------------------------------------------------
def update_annotated_db(db_df, variant_InDB_i, genotype):
    if genotype == 'гетерозигота':
        db_df.loc[variant_InDB_i, 'hetero_num'] += 1
    else:
        db_df.loc[variant_InDB_i, 'homo_num'] += 1
    return db_df


def update_artifact_db(db_df, variant_InDB_i):
    db_df.loc[variant_InDB_i, 'occurrence_num'] += 1
    return db_df


def variant_row_to_annotated_row(variant_row, genotype):
    if genotype == 'гетерозигота':
        variant_row['hetero_num'], variant_row['homo_num'] = [1], [0]
    else:
        variant_row['hetero_num'], variant_row['homo_num'] = [0], [1]
    variant_row['freq'] = [pd.NA]
    return variant_row


def variant_row_to_artifact_row(variant_row):
    variant_row['occurrence_num'] = [1]
    return variant_row


def update_sample_num(db_df):
    db_df.index = list(range(db_df.shape[0]))
    sample_num = db_df.loc[db_df.shape[0] - 1, 'sample_num']
    sample_num_srs = pd.Series([sample_num + 1] * db_df.shape[0])
    db_df['sample_num'] = sample_num_srs
    db_df = db_df.astype({'sample_num': 'Int64'})
    return db_df, sample_num_srs


def update_freq(db_df, sample_num_srs):
    hetero_num_srs, homo_num_srs = db_df['hetero_num'], db_df['homo_num']
    db_df['freq'] = round((hetero_num_srs + homo_num_srs * 2) / (sample_num_srs * 2), 3)
    db_df = db_df.astype({'freq': 'Float64'})
    return db_df


def update_db(variants_df, db_df, name_colname, columns_to_drop):
    db_df = db_df.copy(deep=True)
    variants_df = variants_df.copy(deep=True)
    variants_df = variants_df.drop(columns=columns_to_drop)
    for variant_row_i in list(variants_df.index):
        variant_row = variants_df.loc[variant_row_i, :]
        chrom, pos, ref, alt, genotype = get_variant_info(variant_row)
        variant_name = make_variant_name(chrom, pos, ref, alt)
        variant_InDB_df = db_df[db_df[name_colname] == variant_name]
        # Variant is already in data base, update variant counts in data base
        if variant_InDB_df.shape[0] != 0:
            variant_InDB_i = list(variant_InDB_df.index)[0]
            if name_colname == 'VariantName':
                db_df = update_annotated_db(db_df, variant_InDB_i, genotype)
            else:
                db_df = update_artifact_db(db_df, variant_InDB_i)
        # Variant is not in data base, write variant to data base
        else:
            variant_row = pd.DataFrame({0: variant_row}).T
            variant_row[name_colname] = [variant_name]
            if name_colname == 'VariantName':
                variant_row = variant_row_to_annotated_row(variant_row, genotype)
            else:
                variant_row = variant_row_to_artifact_row(variant_row)
            variant_row['sample_num'] = [pd.NA]
            variant_row = variant_row.astype(db_df.dtypes)
            variant_row = variant_row.loc[:, list(db_df.columns)]
            db_df = pd.concat([variant_row, db_df], ignore_index=True)
    # Update columns by vector operations
    db_df, sample_num_srs = update_sample_num(db_df)
    if name_colname == 'VariantName':
        db_df = update_freq(db_df, sample_num_srs)
    return db_df
# update_db -------------------------------------------------------------------------


# update_patients_database ----------------------------------------------------------
def make_variant_name_with_genotype(chrom, pos, ref, alt, genotype):
    variant_name = make_variant_name(chrom, pos, ref, alt)
    genotype_symbol = 'het' if genotype == 'гетерозигота' else 'hom'
    variant_name_with_genotype = f'{variant_name}-{genotype_symbol}'
    return variant_name_with_genotype


def update_patients_database(variants_df, sample, patients_df):
    patients_df = patients_df.copy(deep=True)
    variant_names = []
    for variant_row_i in list(variants_df.index):
        variant_row = variants_df.loc[variant_row_i, :]
        chrom, pos, ref, alt, genotype = get_variant_info(variant_row)
        variant_name = make_variant_name_with_genotype(chrom, pos, ref, alt, genotype)
        variant_names.append(variant_name)
    variant_names = ','.join(variant_names)
    patients_df.loc[patients_df['request_id'] == sample, 'variants'] = variant_names
    return patients_df
# update_patients_database ----------------------------------------------------------
