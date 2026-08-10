import pandas as pd
import os

def generate_report():
    directory = r'C:\Users\Anas Mohamed\PyCharmMiscProject\SurgicalSets'
    files = ['A1 Sets in details.xlsx', 'A2.xls', 'A3 sets.xlsx', 'Demerdash Order - PO final.xlsx']
    
    with open('surgical_sets_report.md', 'w', encoding='utf-8') as out:
        out.write("# Surgical Sets Analysis Report\n\n")
        out.write("This report provides an overview of the internal sets and included items found in the `SurgicalSets` folder.\n\n")
        
        for f in files:
            filepath = os.path.join(directory, f)
            if not os.path.exists(filepath):
                continue
                
            out.write(f"## File: `{f}`\n\n")
            out.write("| Sheet Name | Total Rows | Identified Items (ArtNo) | Columns |\n")
            out.write("|---|---|---|---|\n")
            try:
                xls = pd.ExcelFile(filepath)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(filepath, sheet_name=sheet)
                    row_count = len(df)
                    
                    # Count valid items by looking for the xx-xxx-xx-xx pattern in any column
                    # Convert all data to string and search for the pattern
                    # We flatten the dataframe to a single series, extract matches, and drop na
                    # This ensures we catch the code even if headers are malformed
                    matches = df.astype(str).apply(lambda col: col.str.contains(r'\d{2}-\d{3}-\d{2}-\d{2}', regex=True, na=False)).any(axis=1)
                    valid_items = int(matches.sum())
                        
                    cols = ", ".join([str(c) for c in df.columns][:5]) + "..." if len(df.columns) > 5 else ", ".join([str(c) for c in df.columns])
                    out.write(f"| {sheet.strip()} | {row_count} | {valid_items} | {cols} |\n")
            except Exception as e:
                out.write(f"| *Error Reading* | - | - | {e} |\n")
            out.write("\n")

if __name__ == '__main__':
    generate_report()
