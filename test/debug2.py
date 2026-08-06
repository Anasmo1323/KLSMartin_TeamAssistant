
import pandas as pd
from spelling_fixes import clean_name

df_kls = pd.ExcelFile('KLS MMC offer.xlsx')
df_mcc = pd.ExcelFile('MCC_OfferList.one copy.xlsx')
# build dict
kls_dict = {}
all_set_names = set()
for sheet in df_kls.sheet_names:
    df = pd.read_excel(df_kls, sheet_name=sheet, header=None)
    current_kls_set = 'UNKNOWN_SET'
    for _, row in df.iterrows():
        is_col0_nan = pd.isna(row[0]) or str(row[0]).strip().lower() == 'nan' or str(row[0]).strip() == ''
        is_col1_nan = pd.isna(row[1]) or str(row[1]).strip().lower() == 'nan' or str(row[1]).strip() == ''
        has_col2 = not pd.isna(row[2]) and str(row[2]).strip() != ''
        if is_col0_nan and is_col1_nan and has_col2:
            current_kls_set = clean_name(str(row[2]).strip())
            all_set_names.add(current_kls_set)
            continue
        if is_col0_nan: continue
        generic_name = clean_name(str(row[0]).strip())
        if sheet not in kls_dict: kls_dict[sheet] = {}
        if current_kls_set not in kls_dict[sheet]: kls_dict[sheet][current_kls_set] = {}
        if generic_name not in kls_dict[sheet][current_kls_set]: kls_dict[sheet][current_kls_set][generic_name] = []
        kls_dict[sheet][current_kls_set][generic_name].append((str(row[1]).strip(), str(row[2]).strip()))

df_tgt = pd.read_excel(df_mcc, sheet_name='ENT')
new_rows = []
current_mcc_set = 'UNKNOWN_SET'
items_to_append = []
last_number = 0

for index, row in df_tgt.iterrows():
    number = row.get('#')
    code = row.get('CODE')
    raw_desc = str(row.get('DESCRIPTION', ''))
    desc = clean_name(raw_desc.strip()) if raw_desc and raw_desc.strip() != 'nan' else ''
    
    is_hash_nan = pd.isna(number) or str(number).strip() == ''
    is_code_nan = pd.isna(code) or str(code).strip() == ''
    has_desc = not pd.isna(row.get('DESCRIPTION')) and desc != ''
    
    if is_hash_nan and has_desc:
        if items_to_append:
            for kls_code, kls_desc in items_to_append:
                last_number += 1
                new_rows.append({'#': last_number, 'CODE': '[KLS] - ' + str(kls_code), 'DESCRIPTION': kls_desc, 'QTY': 1})
            items_to_append = []
            last_number = 0
            
        is_set_header = False
        if desc in all_set_names: is_set_header = True
        elif 'set' in desc.lower() or 'laps' in desc.lower(): is_set_header = True
        
        if is_set_header:
            current_mcc_set = desc
        else:
            current_generic_name = desc
            items_to_append = kls_dict.get('ENT', {}).get(current_mcc_set, {}).get(current_generic_name, []).copy()
    else:
        is_duplicate = False
        if not pd.isna(code):
            existing_code = str(code).strip()
            if any(item[0] == existing_code for item in items_to_append):
                is_duplicate = True
        if is_duplicate: continue
        try:
            last_number = float(number)
        except:
            pass
            
    updated_row = row.to_dict()
    if not pd.isna(row.get('DESCRIPTION')) and desc != '':
        updated_row['DESCRIPTION'] = desc
    new_rows.append(updated_row)

in_set = False
for r in new_rows:
    d = str(r.get('DESCRIPTION', ''))
    if 'Tonsillectomy Set (4)' in d:
        in_set = True
    if in_set:
        print(r.get('#'), '|', r.get('CODE'), '|', d)
    if in_set and 'Needle Holder' in d:
        break

