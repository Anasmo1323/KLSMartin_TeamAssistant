import pandas as pd
import os
import json
import re

def export_report_to_excel():
    directory = r'C:\Users\Anas Mohamed\PyCharmMiscProject\SurgicalSets'
    files = ['A1 Sets in details.xlsx', 'A2.xls', 'A3 sets.xlsx', 'Demerdash Order - PO final.xlsx']
    
    outpath = r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\surgical_sets_report.xlsx'
    
    with pd.ExcelWriter(outpath, engine='openpyxl') as writer:
        
        # 1. Iterate over the 4 files to generate file summaries
        for f in files:
            filepath = os.path.join(directory, f)
            if not os.path.exists(filepath):
                continue
                
            sheet_data = []
            try:
                xls = pd.ExcelFile(filepath)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(filepath, sheet_name=sheet)
                    row_count = len(df)
                    
                    matches = df.astype(str).apply(lambda col: col.str.contains(r'\d{2}-\d{3}-\d{2}-\d{2}', regex=True, na=False)).any(axis=1)
                    valid_items = int(matches.sum())
                        
                    cols = ", ".join([str(c) for c in df.columns][:5]) + "..." if len(df.columns) > 5 else ", ".join([str(c) for c in df.columns])
                    sheet_data.append({
                        "Sheet Name": sheet.strip(),
                        "Total Rows": row_count,
                        "Identified Items (ArtNo)": valid_items,
                        "Columns": cols
                    })
                    
                # Create a DataFrame for this file's summary and write it to a sheet
                # Excel sheet names can only be up to 31 chars
                sheet_name = f.replace('.xlsx', '').replace('.xls', '')[:31]
                df_summary = pd.DataFrame(sheet_data)
                df_summary.to_excel(writer, sheet_name=sheet_name, index=False)
                
            except Exception as e:
                df_summary = pd.DataFrame([{"Error": str(e)}])
                sheet_name = f.replace('.xlsx', '').replace('.xls', '')[:31]
                df_summary.to_excel(writer, sheet_name=sheet_name, index=False)
                
        # 2. Add the parsed A2 Internal Sets summary
        try:
            with open(r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\src\data\A2_parsed_sets.json', encoding='utf-8') as f_json:
                sets = json.load(f_json)
                
            a2_internal_data = []
            for s in sets:
                a2_internal_data.append({
                    "Set Name": s['set_name'],
                    "Item Count": len(s['items'])
                })
                
            df_a2 = pd.DataFrame(a2_internal_data)
            df_a2.to_excel(writer, sheet_name='A2 Internal Sets', index=False)
        except Exception as e:
            print(f"Could not add A2 internal sets: {e}")
            
    print(f"Report successfully saved to {outpath}")

if __name__ == '__main__':
    export_report_to_excel()
