import pandas as pd
import numpy as np

# 1. Define File Paths
f_kls = "KLS MMC offer.xlsx"
f_mcc = "MCC_OfferList.one.numbered.xlsx"
output_file = "MCC_OfferList_Deduplicated.xlsx"

def process_offer_list():
    xls_kls = pd.ExcelFile(f_kls)
    xls_mcc = pd.ExcelFile(f_mcc)
    
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    
    for sheet in xls_mcc.sheet_names:
        df_mcc = pd.read_excel(f_mcc, sheet_name=sheet)
        
        # If the discipline sheet doesn't exist in KLS (or is 'OFFER'), copy and skip
        if sheet not in xls_kls.sheet_names or sheet.upper() == 'OFFER':
            df_mcc.to_excel(writer, sheet_name=sheet, index=False)
            continue
            
        # 2. Extract KLS Data (Header=None because column names are implicit)
        df_kls = pd.read_excel(f_kls, sheet_name=sheet, header=None)
        df_kls = df_kls.drop_duplicates(subset=[0, 1, 2])
        
        kls_dict = {}
        for _, row in df_kls.iterrows():
            item_name = str(row[0]).strip()
            item_code = str(row[1]).strip()
            item_desc = str(row[2]).strip()
            
            # Skip invalid rows
            if pd.isna(row[0]) or item_name.lower() == 'nan' or item_name == '':
                continue
                
            if item_name not in kls_dict:
                kls_dict[item_name] = []
                
            kls_dict[item_name].append({
                'CODE': f"[KLS] - {item_code}",
                'DESCRIPTION': item_desc,
                'QTY': 1
            })
            
        # 3. Process MCC Sheet and Inject KLS Items
        new_rows = []
        current_header = None
        current_counter = 0
        
        for _, row in df_mcc.iterrows():
            desc = str(row.get('DESCRIPTION', '')).strip()
            hash_val = row.get('#', np.nan)
            code_val = row.get('CODE', np.nan)
            
            # Detect a Header Row (No '#' value, CODE is NaN, but has a Description)
            if pd.isna(hash_val) and pd.isna(code_val) and desc:
                
                # A. Flush matching KLS items into the PREVIOUS header block before moving on
                if current_header and current_header in kls_dict:
                    for kls_item in kls_dict[current_header]:
                        current_counter += 1
                        new_rows.append({
                            '#': current_counter,
                            'CODE': kls_item['CODE'],
                            'DESCRIPTION': kls_item['DESCRIPTION'],
                            'QTY': kls_item['QTY']
                        })
                
                # B. Start tracking the NEW header block
                current_header = desc
                current_counter = 0
                new_rows.append(row.to_dict())
                
            # It is a standard item belonging to the current header block
            elif not pd.isna(hash_val):
                current_counter += 1
                updated_row = row.to_dict()
                updated_row['#'] = current_counter # Ensure standard numbering
                new_rows.append(updated_row)
            else:
                new_rows.append(row.to_dict())
                
        # 4. Flush KLS items for the final header in the sheet
        if current_header and current_header in kls_dict:
            for kls_item in kls_dict[current_header]:
                current_counter += 1
                new_rows.append({
                    '#': current_counter,
                    'CODE': kls_item['CODE'],
                    'DESCRIPTION': kls_item['DESCRIPTION'],
                    'QTY': kls_item['QTY']
                })
                
        # Write updated layout to the new file
        df_updated = pd.DataFrame(new_rows)
        df_updated.to_excel(writer, sheet_name=sheet, index=False)
        
    writer.close()
    print(f"Integration complete. File saved sequentially as: {output_file}")

if __name__ == "__main__":
    process_offer_list()