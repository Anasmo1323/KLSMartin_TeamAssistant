
import pandas as pd
import json

def get_kls_items(filename):
    df_kls = pd.ExcelFile(filename)
    items = set()
    for sheet in df_kls.sheet_names:
        df = pd.read_excel(df_kls, sheet_name=sheet, header=None)
        # Check if columns are sufficient
        if len(df.columns) < 3:
            continue
        for _, row in df.iterrows():
            is_col0_nan = pd.isna(row[0]) or str(row[0]).strip().lower() == 'nan' or str(row[0]).strip() == ''
            is_col1_nan = pd.isna(row[1]) or str(row[1]).strip().lower() == 'nan' or str(row[1]).strip() == ''
            
            if not is_col1_nan and not is_col0_nan:
                code = str(row[1]).strip()
                if code != '' and str(code).lower() != 'nan':
                    items.add(code)
    return items

def get_final_kls_items(filename):
    df_final = pd.ExcelFile(filename)
    items = set()
    for sheet in df_final.sheet_names:
        df = pd.read_excel(df_final, sheet_name=sheet)
        for _, row in df.iterrows():
            code = row.get('CODE')
            if not pd.isna(code):
                code_str = str(code).strip()
                if code_str.startswith('[KLS] - '):
                    items.add(code_str.replace('[KLS] - ', '').strip())
                elif code_str in kls_source_items:
                    items.add(code_str)
    return items

kls_source_items = get_kls_items('KLS MMC offer.xlsx')
kls_final_items = get_final_kls_items('MCC_OfferList_Final.xlsx')

missing_in_final = kls_source_items - kls_final_items
extra_in_final = kls_final_items - kls_source_items

print(f'Total distinct KLS items in source: {len(kls_source_items)}')
print(f'Total distinct KLS items in final output: {len(kls_final_items)}')
print(f'Items in source but missing in final: {len(missing_in_final)}')
print(f'Items in final that were not in source: {len(extra_in_final)}')

with open('missing_in_final.txt', 'w', encoding='utf-8') as f:
    for item in sorted(list(missing_in_final)):
        f.write(f'{item}\n')

