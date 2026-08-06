
import pandas as pd
from spelling_fixes import clean_name

def get_kls_structure(filename):
    df_kls = pd.ExcelFile(filename)
    kls_data = {}
    for sheet in df_kls.sheet_names:
        df = pd.read_excel(df_kls, sheet_name=sheet, header=None)
        if len(df.columns) < 3: continue
        current_set = 'UNKNOWN_SET'
        if sheet not in kls_data: kls_data[sheet] = {}
        for _, row in df.iterrows():
            is_col0_nan = pd.isna(row[0]) or str(row[0]).strip().lower() == 'nan' or str(row[0]).strip() == ''
            is_col1_nan = pd.isna(row[1]) or str(row[1]).strip().lower() == 'nan' or str(row[1]).strip() == ''
            has_col2 = not pd.isna(row[2]) and str(row[2]).strip() != ''
            if is_col0_nan and is_col1_nan and has_col2:
                current_set = clean_name(str(row[2]).strip())
                if current_set not in kls_data[sheet]: kls_data[sheet][current_set] = []
                continue
            if is_col0_nan: continue
            if current_set not in kls_data[sheet]: kls_data[sheet][current_set] = []
            gen_name = clean_name(str(row[0]).strip())
            if gen_name != '':
                kls_data[sheet][current_set].append(gen_name)
    return kls_data

def get_mcc_structure(filename):
    df_mcc = pd.ExcelFile(filename)
    mcc_data = {}
    for sheet in df_mcc.sheet_names:
        try:
            df = pd.read_excel(df_mcc, sheet_name=sheet)
        except:
            continue
        if sheet not in mcc_data: mcc_data[sheet] = {}
        current_set = 'UNKNOWN_SET'
        for _, row in df.iterrows():
            number = row.get('#')
            raw_desc = str(row.get('DESCRIPTION', ''))
            desc = clean_name(raw_desc.strip()) if raw_desc and raw_desc.strip() != 'nan' else ''
            
            is_hash_nan = pd.isna(number) or str(number).strip() == ''
            has_desc = not pd.isna(row.get('DESCRIPTION')) and desc != ''
            
            if is_hash_nan and has_desc:
                is_set_header = False
                if 'set' in desc.lower() or 'laps' in desc.lower():
                    is_set_header = True
                
                if is_set_header:
                    current_set = desc
                    if current_set not in mcc_data[sheet]: mcc_data[sheet][current_set] = []
                else:
                    if current_set not in mcc_data[sheet]: mcc_data[sheet][current_set] = []
                    mcc_data[sheet][current_set].append(desc)
    return mcc_data

kls = get_kls_structure('KLS MMC offer.xlsx')
mcc = get_mcc_structure('MCC_OfferList_Final.xlsx')

with open('discrepancies.md', 'w', encoding='utf-8') as f:
    f.write('# Discrepancies Report\n\n')
    for sheet in kls.keys():
        if sheet not in mcc:
            f.write(f'## Sheet {sheet} missing in MCC\n\n')
            continue
            
        f.write(f'## Sheet: {sheet}\n\n')
        
        kls_sets = set(kls[sheet].keys())
        mcc_sets = set(mcc[sheet].keys())
        
        sets_only_in_kls = kls_sets - mcc_sets
        sets_only_in_mcc = mcc_sets - kls_sets
        common_sets = kls_sets.intersection(mcc_sets)
        
        if sets_only_in_kls:
            f.write('### Sets in KLS but NOT in MCC (Entire set skipped)\n')
            for s in sorted(sets_only_in_kls):
                f.write(f'- {s}\n')
            f.write('\n')
            
        if sets_only_in_mcc:
            f.write('### Sets in MCC but NOT in KLS\n')
            for s in sorted(sets_only_in_mcc):
                f.write(f'- {s}\n')
            f.write('\n')
            
        missing_generics = 0
        f.write('### Unmatched Generic Items in Common Sets (in KLS but NOT mapped to MCC)\n')
        for s in sorted(common_sets):
            k_items = set(kls[sheet][s])
            m_items = set(mcc[sheet][s])
            k_only = k_items - m_items
            if k_only:
                f.write(f'**{s}**\n')
                for item in sorted(k_only):
                    f.write(f'- {item}\n')
                    missing_generics += 1
                f.write('\n')

