import os
import json
import warnings
import pandas as pd
from semantic_grouper import SemanticGrouper
from core.utils import resource_path

warnings.filterwarnings('ignore')

def main():
    print("Loading data...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "data", "KLS_Product_Families.json")
    output_excel = os.path.join(base_dir, "data", "KLS_Product_Families.xlsx")
    raw_excel_path = os.path.join(base_dir, "data", "KLS_All_Products.xlsx")
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        print("Please run instrument_parser.py first to generate the base data.")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Flatten the JSON into a dataframe
    rows = []
    for family_name, group_data in data.items():
        if "items" in group_data:
            for item in group_data["items"]:
                item["original_family"] = family_name
                rows.append(item)
                
    df = pd.DataFrame(rows)
    
    print(f"Loaded {len(df)} items.")
    
    if 'description' not in df.columns or 'brochures' not in df.columns:
        print("Loading raw Excel to get full descriptions...")
        raw_df = pd.read_excel(raw_excel_path)
        df = pd.merge(df, raw_df[['code', 'description', 'brochures']], on='code', how='left')
        
    print("Starting Semantic Grouping Pipeline...")
    model_path = resource_path("models/Qwen2.5-14B-Instruct-Q4_K_M.gguf")
    
    if not os.path.exists(model_path):
        print(f"LLM model not found at {model_path}. Please download it.")
        return
        
    grouper = SemanticGrouper(df, model_path=model_path, cache_dir="cache")
    df_clean = grouper.run()
    
    print("Saving updated JSON and Excel...")
    
    # Use build_json from instrument_parser to maintain exact same structure
    from instrument_parser import build_json
    final_dict = build_json(df_clean)
        
    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, indent=4, ensure_ascii=False)
        
    # Write Excel
    df_clean.to_excel(excel_path, index=False)
    
    print("Done! Semantic grouping complete.")

if __name__ == "__main__":
    main()
