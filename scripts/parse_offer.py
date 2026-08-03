import pandas as pd
import json
import re
import sys
import os

# Import the parsing functions from instrument_parser.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from instrument_parser import parse_instrument_regex

def parse_offer_list():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, 'data', 'MCC_OfferList.xlsx')
    all_products_path = os.path.join(base_dir, 'data', 'KLS_All_Products.xlsx')
    output_json_path = os.path.join(base_dir, 'offer_webapp', 'src', 'data', 'offer_catalog.json')
    
    print("Loading data...")
    offer_df = pd.read_excel(excel_path)
    all_products_df = pd.read_excel(all_products_path)
    
    all_products_df['code'] = all_products_df['code'].astype(str).str.strip()
    lookup_dict = all_products_df.set_index('code').to_dict('index')

    catalog = []
    
    excel_file = pd.ExcelFile(excel_path)
    
    for sheet_name in excel_file.sheet_names:
        offer_df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        current_set = {
            "set_id": f"{sheet_name}_General",
            "set_name": sheet_name,  # Default set name to sheet name
            "groups": []
        }
        
        current_category = {
            "name": sheet_name,
            "sets": [current_set]
        }
        current_group = None
        
        for idx, row in offer_df.iterrows():
            has_hash = pd.notna(row['#'])
            
            if not has_hash:
                if pd.isna(row['DESCRIPTION']):
                    continue
                    
                header_name = str(row['DESCRIPTION']).strip()
                header_qty = float(row['QTY']) if pd.notna(row['QTY']) else 1.0
                
                # If we already have a group but it's empty, the previous group was actually a Set!
                if current_group and len(current_group['options']) == 0:
                    # The previous header was an Internal Set
                    current_set = {
                        "set_id": f"{sheet_name}_set_{idx}",
                        "set_name": current_group['group_name'],
                        "groups": []
                    }
                    current_category["sets"].append(current_set)
                    # Remove the empty group from the previous set
                    if len(current_category["sets"][-2]["groups"]) > 0:
                        current_category["sets"][-2]["groups"].pop()
                
                current_group = {
                    "group_id": f"{sheet_name}_{idx}_{str(row['CODE']).strip() if pd.notna(row['CODE']) else ''}",
                    "group_name": header_name,
                    "required_qty": header_qty,
                    "options": []
                }
                current_set["groups"].append(current_group)
                
            else:
                code = str(row['CODE']).strip() if pd.notna(row['CODE']) else ""
                item_qty = float(row['QTY']) if pd.notna(row['QTY']) else None
                desc = str(row['DESCRIPTION']).strip() if pd.notna(row['DESCRIPTION']) else ""
                
                base_code_match = re.match(r"^(\d{2}-\d{2})", code)
                base_code = base_code_match.group(1) if base_code_match else code
                
                extracted = parse_instrument_regex(desc)
                extracted = {k: v for k, v in extracted.items() if v is not None}
                
                item = {
                    "option_id": str(row['#']).replace('.0', '').strip(),
                    "code": code,
                    "base_code": base_code,
                    "basic_description": desc,
                    "qty": item_qty,
                    "image_url": None,
                    "extracted_features": extracted,
                    "details": {}
                }
                
                if code in lookup_dict:
                    kls_data = lookup_dict[code]
                    for k, v in kls_data.items():
                        if pd.notna(v) and str(v).strip() != "":
                            if k not in ['code', 'url', 'id', 'description_arabic']:
                                item["details"][k] = v
                
                if current_group:
                    current_group["options"].append(item)
                    
        catalog.append(current_category)

    # Filter out empty sets and groups
    for cat in catalog:
        for s in cat["sets"]:
            s["groups"] = [g for g in s["groups"] if len(g["options"]) > 0]
        cat["sets"] = [s for s in cat["sets"] if len(s["groups"]) > 0]
    catalog = [c for c in catalog if len(c["sets"]) > 0]

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=4)
        
    print(f"Parsed successfully to {output_json_path}")

if __name__ == "__main__":
    parse_offer_list()
