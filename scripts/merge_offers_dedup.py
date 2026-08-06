import pandas as pd
import numpy as np
import os
from spelling_fixes import clean_name

def merge_offers(source_file, target_file, output_file):
    print(f"Reading source file: {source_file}")
    try:
        xls_source = pd.ExcelFile(source_file)
    except FileNotFoundError:
        print(f"Error: {source_file} not found.")
        return

    print(f"Reading target file: {target_file}")
    try:
        xls_target = pd.ExcelFile(target_file)
    except FileNotFoundError:
        print(f"Error: {target_file} not found.")
        return

    # Process source data: deduplicate and build dictionary grouped by sheet and set
    # Columns are: 0: Generic Name, 1: Item Code, 2: Description
    kls_dict = {}
    all_generic_names = set()
    all_set_names = set()
    for sheet in xls_source.sheet_names:
        df_src = pd.read_excel(xls_source, sheet_name=sheet, header=None)
        if len(df_src.columns) >= 3:
            current_kls_set = "UNKNOWN_SET"
            for _, row in df_src.iterrows():
                is_col0_nan = pd.isna(row[0]) or str(row[0]).strip().lower() == 'nan' or str(row[0]).strip() == ''
                is_col1_nan = pd.isna(row[1]) or str(row[1]).strip().lower() == 'nan' or str(row[1]).strip() == ''
                has_col2 = not pd.isna(row[2]) and str(row[2]).strip() != ''
                
                # Detect KLS Set Header (col 0 and col 1 are NaN, col 2 has text)
                if is_col0_nan and is_col1_nan and has_col2:
                    current_kls_set = clean_name(str(row[2]).strip())
                    all_set_names.add(current_kls_set)
                    continue
                    
                if is_col0_nan:
                    continue
                    
                generic_name = clean_name(str(row[0]).strip())
                item_code = str(row[1]).strip()
                description = str(row[2]).strip()
                
                if generic_name == '':
                    continue
                    
                all_generic_names.add(generic_name)
                
                if sheet not in kls_dict:
                    kls_dict[sheet] = {}
                if current_kls_set not in kls_dict[sheet]:
                    kls_dict[sheet][current_kls_set] = {}
                if generic_name not in kls_dict[sheet][current_kls_set]:
                    kls_dict[sheet][current_kls_set][generic_name] = []
                
                # Store unique items
                item_tuple = (item_code, description)
                if item_tuple not in kls_dict[sheet][current_kls_set][generic_name]:
                    kls_dict[sheet][current_kls_set][generic_name].append(item_tuple)

    print(f"Built grouped mapping with {len(all_generic_names)} distinct generic items across {len(kls_dict)} sheets.")

    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        for sheet in xls_target.sheet_names:
            df_tgt = pd.read_excel(xls_target, sheet_name=sheet)
            
            # If sheet is OFFER or not in source sheets, bypass/copy
            if sheet.upper() == 'OFFER' or sheet not in xls_source.sheet_names:
                df_tgt.to_excel(writer, sheet_name=sheet, index=False)
                continue
                
            print(f"Processing sheet: {sheet}")
            
            new_rows = []
            current_mcc_set = "UNKNOWN_SET"
            current_generic_name = None
            items_to_append = []
            last_number = 0
            
            for index, row in df_tgt.iterrows():
                number = row.get('#')
                code = row.get('CODE')
                raw_desc = str(row.get('DESCRIPTION', ''))
                desc = clean_name(raw_desc.strip()) if raw_desc and raw_desc.strip() != 'nan' else ''
                
                # Check for Generic Item Header or Set Header.
                is_hash_nan = pd.isna(number) or str(number).strip() == ''
                is_code_nan = pd.isna(code) or str(code).strip() == ''
                has_desc = not pd.isna(row.get('DESCRIPTION')) and desc != ''
                
                # If we encounter a new header, append any pending KLS items from the previous header
                if is_hash_nan and has_desc:
                    if items_to_append:
                        # Deduplicate KLS items to avoid repeating identical items within the same set
                        unique_items = []
                        seen = set()
                        for kls_code, kls_desc in items_to_append:
                            if (kls_code, kls_desc) not in seen:
                                seen.add((kls_code, kls_desc))
                                unique_items.append((kls_code, kls_desc))
                                
                        for kls_code, kls_desc in unique_items:
                            last_number += 1
                            new_rows.append({
                                '#': last_number,
                                'CODE': f"[KLS] - {kls_code}",
                                'DESCRIPTION': kls_desc,
                                'QTY': 1
                            })
                        items_to_append = []
                        last_number = 0
                    
                    # Detect if this is a Set Header or Generic Item
                    is_set_header = False
                    
                    if desc in all_set_names:
                        is_set_header = True
                    elif 'set' in desc.lower() or 'laps' in desc.lower():
                        is_set_header = True
                    
                    if is_set_header:
                        current_mcc_set = desc
                        items_to_append = []
                    else:
                        current_generic_name = desc
                        items_to_append = kls_dict.get(sheet, {}).get(current_mcc_set, {}).get(current_generic_name, []).copy()
                else:
                    # It's an existing option (numbered row)
                    is_duplicate = False
                    if not pd.isna(code):
                        existing_code = str(code).strip()
                        if any(item[0] == existing_code for item in items_to_append):
                            is_duplicate = True
                            
                    if is_duplicate:
                        continue
                        
                    try:
                        last_number = float(number)
                    except (ValueError, TypeError):
                        pass
                
                # Add the current row to the new list with cleaned description if available
                updated_row = row.to_dict()
                if not pd.isna(row.get('DESCRIPTION')) and desc != '':
                    updated_row['DESCRIPTION'] = desc
                new_rows.append(updated_row)
                
            # Append any remaining items at the end of the sheet
            if items_to_append:
                unique_items = []
                seen = set()
                for kls_code, kls_desc in items_to_append:
                    if (kls_code, kls_desc) not in seen:
                        seen.add((kls_code, kls_desc))
                        unique_items.append((kls_code, kls_desc))
                        
                for kls_code, kls_desc in unique_items:
                    last_number += 1
                    new_rows.append({
                        '#': last_number,
                        'CODE': f"[KLS] - {kls_code}",
                        'DESCRIPTION': kls_desc,
                        'QTY': 1
                    })
            
            new_df = pd.DataFrame(new_rows)
            
            # Style the rows
            def style_rows(r):
                num = r.get('#')
                cd = r.get('CODE')
                d = r.get('DESCRIPTION')
                
                is_hash_nan = pd.isna(num) or str(num).strip() == ''
                is_code_nan = pd.isna(cd) or str(cd).strip() == ''
                has_desc = not pd.isna(d) and str(d).strip() != ''
                
                if is_hash_nan and has_desc:
                    if not is_code_nan or str(d).strip() in kls_dict:
                        # Generic Item Header (Light Yellow)
                        return ['background-color: #FFF2CC; font-weight: bold'] * len(r)
                    else:
                        # Set Header (Light Blue)
                        return ['background-color: #BDD7EE; font-weight: bold'] * len(r)
                return [''] * len(r)
                
            styled_df = new_df.style.apply(style_rows, axis=1)
            styled_df.to_excel(writer, sheet_name=sheet, index=False)
            
    print(f"Successfully saved to {output_file}")

if __name__ == "__main__":
    SOURCE = "KLS MMC offer.xlsx"
    TARGET = "anas2.xlsx"
    OUTPUT = "MCC_OfferList_Deduplicated.xlsx"
    merge_offers(SOURCE, TARGET, OUTPUT)