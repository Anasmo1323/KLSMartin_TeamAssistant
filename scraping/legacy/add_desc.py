import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

def scrape_missing_descriptions(file_path):
    # Load the master combined file
    df = pd.read_csv(file_path)
    
    # Identify rows where description is missing (NaN or empty string)
    missing_desc_mask = df['description'].isna() | (df['description'] == "")
    total_missing = missing_desc_mask.sum()
    
    print(f"Found {total_missing} items missing descriptions. Starting extraction...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    count = 0
    # Iterate only over the rows missing descriptions
    for index, row in df[missing_desc_mask].iterrows():
        url = row['product_url']
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # The product description is typically located in the main h1 tag on the product page
                h1_tag = soup.find('h1')
                
                if h1_tag:
                    clean_desc = h1_tag.text.strip()
                    df.at[index, 'description'] = clean_desc
                    print(f"[{count+1}/{total_missing}] Updated {row['code']}: {clean_desc}")
                else:
                    print(f"[{count+1}/{total_missing}] No H1 tag found for {row['code']}")
            else:
                print(f"[{count+1}/{total_missing}] HTTP {response.status_code} for {row['code']}")
                
        except Exception as e:
            print(f"[{count+1}/{total_missing}] Error fetching {row['code']}: {e}")
            
        count += 1
        
        # Save progress every 100 items to prevent data loss in case of a crash or block
        if count % 100 == 0:
            df.to_csv(file_path, index=False)
            print("--- Intermediate progress saved ---")
            
        # 1.5 second delay to respect server load and avoid IP bans
        time.sleep(1.5)
        
    # Final save
    df.to_csv(file_path, index=False)
    print("Extraction complete. Master CSV updated.")

if __name__ == "__main__":
    scrape_missing_descriptions("klsmartin_master_combined.csv")