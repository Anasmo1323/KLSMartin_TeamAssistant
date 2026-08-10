import pandas as pd
import json
import re

def parse_a2_xls():
    filepath = r'C:\Users\Anas Mohamed\PyCharmMiscProject\SurgicalSets\A2.xls'
    outpath = r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\src\data\A2_parsed_sets.json'
    
    print("Reading A2.xls...")
    df = pd.read_excel(filepath, header=None)
    
    sets = []
    current_set = None
    
    for idx, row in df.iterrows():
        # Clean values
        art_no = str(row[1]).strip() if pd.notna(row[1]) else ''
        description = str(row[2]).strip() if pd.notna(row[2]) else ''
        
        # Check if this is an item row (has a valid ArtNo)
        # Using the pattern xx-xxx-xx-xx
        if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', art_no):
            if current_set is not None:
                qty = row[5]
                current_set['items'].append({
                    "art_no": art_no,
                    "description": description,
                    "qty": float(qty) if pd.notna(qty) else 1.0
                })
        else:
            # If it's not an item, and description is not empty and not 'NaN', it might be a set header
            if description and description.lower() != 'nan' and not description.startswith('Tray Name'):
                # Save previous set
                if current_set and len(current_set['items']) > 0:
                    sets.append(current_set)
                    
                current_set = {
                    "set_name": description,
                    "items": []
                }
                
    # Append the last set
    if current_set and len(current_set['items']) > 0:
        sets.append(current_set)
        
    print(f"Successfully parsed {len(sets)} sets.")
    
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(sets, f, indent=2, ensure_ascii=False)
    print(f"Saved to {outpath}")

if __name__ == '__main__':
    parse_a2_xls()
