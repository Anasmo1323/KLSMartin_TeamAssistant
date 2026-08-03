import pandas as pd
import urllib.parse
import requests
from bs4 import BeautifulSoup
import time
import os

def build_unified_master(csv_path, excel_path, output_path):
    print("--- Phase 1: Data Merging and Deduplication ---")
    
    # Load source files
    df_csv = pd.read_csv(csv_path)
    df_excel = pd.read_excel(excel_path)
    
    # Standardize primary keys
    df_csv['code'] = df_csv['code'].astype(str).str.strip()
    df_excel['Code'] = df_excel['Code'].astype(str).str.strip()
    
    # Deduplicate Excel data by aggregating catalogues
    df_excel_agg = df_excel.groupby('Code')['Catalogue'].apply(
        lambda x: '; '.join(x.dropna().unique())
    ).reset_index()
    
    # Isolate net-new codes from the Excel dataset
    existing_codes = set(df_csv['code'])
    new_data = df_excel_agg[~df_excel_agg['Code'].isin(existing_codes)].copy()
    
    # Structure the new data to match the CSV schema
    new_formatted = pd.DataFrame()
    new_formatted['code'] = new_data['Code']
    new_formatted['description'] = ""
    new_formatted['brochures'] = new_data['Catalogue']
    
    # Generate static URL structures
    new_formatted['ifu_link'] = new_formatted['code'].apply(
        lambda x: f'https://www.klsmartin.com/en/services/instructions-for-use/#%7B%22fulltext%22:%22{urllib.parse.quote(x)}%22%7D'
    )
    new_formatted['product_url'] = new_formatted['code'].apply(
        lambda x: f'https://www.klsmartin.com/shop/en/products/product/{x}/'
    )
    
    # Combine datasets
    master_df = pd.concat([df_csv, new_formatted], ignore_index=True)
    print(f"Data combined successfully. Total unique items: {len(master_df)}")

    print("\n--- Phase 2: Scraping Missing Descriptions ---")
    
    # Isolate records requiring data extraction
    missing_mask = master_df['description'].isna() | (master_df['description'] == "")
    total_missing = missing_mask.sum()
    print(f"Identified {total_missing} items requiring descriptions.")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    count = 0
    for index, row in master_df[missing_mask].iterrows():
        url = row['product_url']
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract primary tag data
                code_el = soup.select_one("h1")
                scraped_code = code_el.get_text(strip=True).replace("Art. No.", "").strip() if code_el else ""

                desc_el = soup.select_one("h2")
                description = desc_el.get_text(strip=True) if desc_el else ""

                # Validation Logic: Prevent the "Art. No." template mirroring bug
                if "Art. No." in description or (scraped_code and scraped_code in description):
                    description = ""
                    
                # Update DataFrame
                master_df.at[index, 'description'] = description
                print(f"[{count+1}/{total_missing}] Parsed {row['code']}: {description if description else 'No Description Available'}")
            
            else:
                print(f"[{count+1}/{total_missing}] HTTP {response.status_code} for {row['code']}")
                
        except Exception as e:
            print(f"[{count+1}/{total_missing}] Connection error for {row['code']}: {e}")
            
        count += 1
        
        # Save state incrementally
        if count % 100 == 0:
            master_df.to_csv(output_path, index=False)
            print(f"--- State saved at {count} processed items ---")
            
        # Throttling to respect server limits
        time.sleep(1.5)

    # Final commit
    master_df.to_csv(output_path, index=False)
    print(f"\nExecution finished. Master file saved to: {output_path}")

if __name__ == "__main__":
    build_unified_master(
        csv_path="klsmartin_products.csv", 
        excel_path="klsmartin_allproducts2.xlsx", 
        output_path="klsmartin_master_combined.csv"
    )