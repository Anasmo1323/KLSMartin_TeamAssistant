import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def extract_catalogues(item_code):
    # Construct the exact product URL
    url = f"https://www.klsmartin.com/shop/en/products/product/{item_code}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to retrieve {item_code}: HTTP {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        catalogues = []
        
        # Locate all anchor tags containing links to the mediathek PDFs
        for a_tag in soup.find_all('a', href=True):
            if '/mediathek/' in a_tag['href'] and '.pdf' in a_tag['href']:
                # Clean the extracted text to remove hidden newline characters
                clean_text = a_tag.text.strip()
                if clean_text:
                    catalogues.append(clean_text)
                    
        return catalogues
        
    except Exception as e:
        print(f"Error parsing {item_code}: {str(e)}")
        return []

# Execute the pipeline for a list of target codes
target_codes = ["10-130-03-07", "10-100-04-07"]
extracted_data = []

for code in target_codes:
    catalogue_list = extract_catalogues(code)
    
    extracted_data.append({
        "Code": code,
        # Join the list of catalogues into a single comma-separated string
        "Catalogues": ", ".join(catalogue_list) 
    })
    
    # Introduce a delay to prevent connection termination by the host server
    time.sleep(1.5)

# Convert to a DataFrame for export
df = pd.DataFrame(extracted_data)
print(df)

# Export to Excel to update your local inventory database
df.to_excel("Scraped_Catalogues.xlsx", index=False)