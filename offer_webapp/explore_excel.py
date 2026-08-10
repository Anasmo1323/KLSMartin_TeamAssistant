import pandas as pd
import os
import json
import xlrd  # Ensure xlrd is available for .xls

def explore_excel(filepath):
    print(f"\n--- Exploring: {os.path.basename(filepath)} ---")
    try:
        # Load the excel file
        xls = pd.ExcelFile(filepath)
        sheet_names = xls.sheet_names
        print(f"Sheets ({len(sheet_names)}): {sheet_names}")
        
        for sheet in sheet_names:
            print(f"\nSheet: {sheet}")
            df = pd.read_excel(filepath, sheet_name=sheet, nrows=5)  # read first 5 rows to understand structure
            print(f"Columns: {list(df.columns)}")
            
            # Show number of non-null values for first 5 rows
            print(df.head(2).to_string())
    except Exception as e:
        print(f"Error exploring {filepath}: {e}")

if __name__ == '__main__':
    directory = r'C:\Users\Anas Mohamed\PyCharmMiscProject\SurgicalSets'
    files = ['A1 Sets in details.xlsx', 'A2.xls', 'A3 sets.xlsx', 'Demerdash Order - PO final.xlsx']
    for f in files:
        explore_excel(os.path.join(directory, f))
