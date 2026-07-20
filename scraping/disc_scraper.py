import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

def update_missing_products():
    excel_file = 'KLS_All_Products.xlsx'
    
    if not os.path.exists(excel_file):
        print(f"Error: '{excel_file}' not found.")
        return

    df = pd.read_excel(excel_file, dtype=str)
    missing_codes = [
        "13-248-13-07", "13-313-62-09", "13-385-13-07", "13-385-14-07",
        "24-416-32-07", "24-417-26-07", "24-417-27-07", "24-420-25-07",
        "24-422-24-07", "24-423-25-07", "24-424-01-07", "24-425-09-07",
        "24-425-15-07", "24-427-25-07", "24-429-25-07", "24-431-17-07",
        "24-433-24-07", "24-434-23-07", "24-437-20-07", "24-437-25-07",
        "24-438-14-07", "24-439-18-07", "24-451-26-07", "24-453-16-07",
        "24-455-17-07", "31-881-90-98", "38-468-02-04", "80-996-25-04"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    base_product_url = "https://www.klsmartin.com/shop/en/products/product/"
    updated_count = 0

    for code in missing_codes:
        product_url = f"{base_product_url}{code}/"
        print(f"Scraping data for: {code}")

        try:
            res = requests.get(product_url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Corrected HTML selector based on KLS Martin structure
                title_tag = soup.find('h2', class_='product-name') 
                description = title_tag.get_text(strip=True) if title_tag else "No Description Found"

                # Update the DataFrame where the code matches
                df.loc[df['code'] == code, 'description'] = description
                updated_count += 1
            else:
                print(f"  Failed HTTP {res.status_code}: Product page might be discontinued or hidden.")

            # Rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"  Error retrieving {code}: {e}")

    # Save the updated database
    df.to_excel(excel_file, index=False)
    print(f"\nProcess complete. Successfully updated {updated_count} items in {excel_file}.")

if __name__ == '__main__':
    update_missing_products()