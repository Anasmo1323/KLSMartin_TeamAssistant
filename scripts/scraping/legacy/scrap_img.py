import os
import time
import random
import re
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

def clean_filename(name):
    """Removes invalid characters for Windows filenames."""
    return re.sub(r'[\\/*?:"<>|]', "", str(name))

def build_offline_image_database(csv_path, max_passes=3):
    # Setup the local images directory
    base_dir = os.path.dirname(csv_path)
    images_dir = os.path.join(base_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Configure resilient session to handle connection drops
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Outer loop to reiterate over the file for failed downloads
    for pass_num in range(1, max_passes + 1):
        df = pd.read_csv(csv_path)
        
        if 'local_image_path' not in df.columns:
            df['local_image_path'] = ""
            
        # Target empty paths AND paths that contain specific failure error strings
        retriable_statuses = ["", "Download Failed", "HTTP Error"]
        missing_mask = df['local_image_path'].isna() | df['local_image_path'].isin(retriable_statuses)
        total_missing = missing_mask.sum()
        
        if total_missing == 0:
            print(f"Pass {pass_num}: No missing images left to process. Finishing.")
            break
            
        print(f"--- Starting Pass {pass_num}/{max_passes}: {total_missing} items to process ---")
        
        count = 0
        for index, row in df[missing_mask].iterrows():
            product_code = row['code']
            url = row.get('product_url', f"https://www.klsmartin.com/shop/en/products/product/{product_code}/")
            
            try:
                # 1. Scrape the image URL
                response = session.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    img_tag = soup.select_one('.product-detail-swiper img')
                    
                    if img_tag and img_tag.has_attr('src'):
                        img_src = img_tag['src']
                        if img_src.startswith('/'):
                            img_src = "https://www.klsmartin.com" + img_src
                            
                        # 2. Download the image data
                        # 2. Download the image data
                        img_response = session.get(img_src, headers=headers, timeout=20)
                        if img_response.status_code == 200:
                            # 3. Save directly as PNG to preserve quality and transparency
                            image_data = Image.open(BytesIO(img_response.content))
                            
                            # Convert CMYK print-format images to RGB to comply with PNG standards
                            if image_data.mode == 'CMYK':
                                image_data = image_data.convert('RGB')
                            
                            safe_filename = f"{clean_filename(product_code)}.png"
                            save_path = os.path.join(images_dir, safe_filename)
                            
                            image_data.save(save_path, 'PNG')
                            
                            # 4. Update CSV with relative path
                            df.at[index, 'local_image_path'] = os.path.join("images", safe_filename)
                            print(f"[{count+1}/{total_missing}] Saved {safe_filename}")
                        else:
                            df.at[index, 'local_image_path'] = "Download Failed"
                    else:
                        df.at[index, 'local_image_path'] = "No Image"
                        print(f"[{count+1}/{total_missing}] No image found on page for {product_code}")
                else:
                    df.at[index, 'local_image_path'] = "HTTP Error"
                    
            except Exception as e:
                print(f"[{count+1}/{total_missing}] Error processing {product_code}: {e}")
                df.at[index, 'local_image_path'] = "Download Failed" # Catch timeout errors here
                
            count += 1
            
            if count % 50 == 0:
                df.to_csv(csv_path, index=False)
                print(f"--- Progress saved at {count} items ---")
                
            # Randomize delay to reduce server load
            time.sleep(random.uniform(1.5, 3.5))
            
        # Final save for the current pass
        df.to_csv(csv_path, index=False)
        print(f"Pass {pass_num} complete.")
        
    print("Offline database build operation finished.")

if __name__ == "__main__":
    target_file = r"KLS_All_Products.csv"
    build_offline_image_database(target_file)