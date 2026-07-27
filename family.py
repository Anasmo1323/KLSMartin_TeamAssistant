import os
import re
import pandas as pd
import numpy as np

def extract_family_name(description):
    """
    Parses unstructured surgical instrument descriptions to extract the root family name 
    by splitting at commas and truncating upon encountering a variant modifier or dimension.
    """
    if pd.isna(description) or not isinstance(description, str):
        return np.nan
        
    # 1. Variant modifiers, materials, colors, and mechanisms
    modifiers = [
        # Shapes & Orientations
        r'\b(straight|str\.?|st\.?|curved|cvd\.?|cv\.?|angled|ang\.?)\b',
        r'\b(right|ri\.?|rt|left|le\.?|lt|upwards|upw\.?|downwards|downw\.?|bkw\.?)\b',
        r'\b(blunt|bl\.?|sharp|sh\.?|pointed|bayonet|bay\.?|malleable|mall\.?|flexible|flex\.?|rigid|solid|hollow)\b',
        # Features & Mechanisms
        r'\b(with|w/|w/o|without|ratchet|lock|fenestrated|fen\.?|serrated|serr\.?|smooth|toothed|teeth|prongs)\b',
        # Materials & Inventory Status
        r'\b(sterile|ster\.?|demo|titanium|ti|steel|tc|gold|pack|set|container|tray|module)\b',
        # Colors
        r'\b(blue|green|red|black|yellow|grey|orange|purple|white|violet|brown)\b'
    ]
    
    # 2. Dimensional patterns, symbols, and sizing nomenclature
    dimension_pattern = (
        r'\d+\.?\d*\s*(cm|mm|inch|in|ch|°|g|ml|cc|v)\b|' # Captures 18 cm, 5mm, 90°, 250 g
        r'\b(length|width|height|depth|size|figure|fig\.?|no\.?|pack of)\b|' # Explicit dimension keywords
        r'ø|' # Diameter symbol
        r'\b\d+\s*(x|\*)\s*\d+\b|' # Grid/Plate sizes like 5x10mm or 30x30
        r'\b\d+\s*/\s*\d+\b' # Fractions like 1/2 or 3/8
    )
    
    # Compile regex for execution speed
    modifier_regex = re.compile('|'.join(modifiers), re.IGNORECASE)
    dimension_regex = re.compile(dimension_pattern, re.IGNORECASE)

    # 3. Split the description into hierarchical chunks
    parts = [p.strip() for p in description.split(',')]
    family_parts = []

    # 4. Iterate through chunks and build the family name
    for part in parts:
        if modifier_regex.search(part) or dimension_regex.search(part):
            break
        family_parts.append(part)

    # Fallback logic: If the first chunk triggered a stop, keep it as the family
    if not family_parts and parts:
        family_parts.append(parts[0])

    return ", ".join(family_parts).strip()

def generate_product_families():
    # File Configuration
    base_dir = r"C:\Users\Anas Mohamed\PyCharmMiscProject"
    master_file = os.path.join(base_dir, "KLS_All_Products.xlsx")
    
    print(f"Loading master database from {master_file}...")
    try:
        df_master = pd.read_excel(master_file)
    except FileNotFoundError:
        print(f"Error: Could not locate {master_file}.")
        return

    if 'description' not in df_master.columns:
        print("Error: 'description' column not found in the master file.")
        return

    print("Executing heuristic text parsing on descriptions...")
    
    # Apply the parsing function to create/update the Family column
    df_master['Family'] = df_master['description'].apply(extract_family_name)

    # Preview the transformations in the console
    print("\nSample Groupings Generated:")
    sample_df = df_master[['code', 'description', 'Family']].dropna().head(10)
    for _, row in sample_df.iterrows():
        print(f"Code: {row['code']}")
        print(f"Desc: {row['description']}")
        print(f"Fam : {row['Family']}\n")

    # Save Output
    print(f"Saving updated master file to {master_file}...")
    df_master.to_excel(master_file, index=False)
    print("Data engineering process complete.")

if __name__ == '__main__':
    generate_product_families()