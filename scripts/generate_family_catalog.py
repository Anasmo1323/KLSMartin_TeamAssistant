import pandas as pd
import json
import re
import os
import sys

# Import the parsing functions from instrument_parser.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from instrument_parser import parse_instrument_regex

def generate_family_catalog():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_products_path = os.path.join(base_dir, 'data', 'KLS_All_Products.xlsx')
    output_json_path = 'offer_webapp/src/data/family_catalog.json'
    
    print("Loading master catalog...")
    df = pd.read_excel(all_products_path)
    
    # Clean data
    df['code'] = df['code'].astype(str).str.strip()
    df['description'] = df['description'].astype(str).str.strip()
    
    family_catalog = {}
    
    print("Processing items...")
    for idx, row in df.iterrows():
        code = row['code']
        if pd.isna(code) or code == 'nan' or code == "":
            continue
            
        desc = row['description'] if pd.notna(row['description']) else ""
        
        # Extract 5-char variation base code (xx-xx)
        base_code_match = re.match(r"^(\d{2}-\d{2})", code)
        if not base_code_match:
            continue
            
        base_code = base_code_match.group(1)
        
        # Extract features
        extracted = parse_instrument_regex(desc)
        extracted = {k: v for k, v in extracted.items() if v is not None}
        
        item = {
            "code": code,
            "base_code": base_code,
            "basic_description": desc,
            "extracted_features": extracted,
            "details": {
                "description": row.get('description', desc)
            }
        }
        
        if base_code not in family_catalog:
            family_catalog[base_code] = []
            
        family_catalog[base_code].append(item)
        
    print(f"Grouped into {len(family_catalog)} families.")
    
    # Save to JSON
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(family_catalog, f, indent=4)
        
    print(f"Saved successfully to {output_json_path}")

if __name__ == "__main__":
    generate_family_catalog()
