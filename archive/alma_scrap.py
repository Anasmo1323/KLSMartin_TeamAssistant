import os
import requests
import pandas as pd
import urllib3
from playwright.sync_api import sync_playwright

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_auth_token():
    """Automates the login process to capture the required API token."""
    EMAIL = "albear@technowave-eg.com"
    PASSWORD = "KLSteam@123"
    LOGIN_URL = "https://alma.klsmartin.com/kls-library/quick-converter"
    
    auth_token = None

    print("Initializing browser automation for authentication...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        def capture_token(request):
            nonlocal auth_token
            if "/api/backend/" in request.url:
                headers = request.headers
                if "authorization" in headers:
                    auth_token = headers["authorization"]

        page.on("request", capture_token)

        page.goto(LOGIN_URL)
        
        page.wait_for_selector('input[placeholder="Email *"]')
        page.fill('input[placeholder="Email *"]', EMAIL)
        page.click('button:has-text("Login / Sign up")')

        page.wait_for_selector('input[type="password"]', timeout=15000)
        page.fill('input[type="password"]', PASSWORD)
        page.click('button[type="submit"], button#next')

        print("Waiting for session initialization and token capture...")
        page.wait_for_load_state("networkidle", timeout=30000)
        
        browser.close()
        
    return auth_token

def search_competitor_sku(sku_list, auth_token):
    """Queries the Quick Converter API with the captured token."""
    if not auth_token:
        print("Error: No valid authorization token provided.")
        return None
        
    api_endpoint = "https://alma.klsmartin.com/api/backend/CompetitorProduct/Search"
    
    headers = {
        "Accept": "application/json",
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Host": "alma.klsmartin.com",
        "Origin": "https://alma.klsmartin.com",
        "Referer": "https://alma.klsmartin.com/kls-library/quick-converter"
    }
    
    payload = {
        "searchTerms": sku_list
    }
    
    print(f"Executing conversion query for {len(sku_list)} items...")
    try:
        response = requests.post(api_endpoint, headers=headers, json=payload, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Request Failed. HTTP Status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Request execution error: {e}")
        return None

if __name__ == '__main__':
    # 1. Automatically fetch the token
    token = get_auth_token()
    
    if token:
        print("Authentication successful.")
        
        # 2. Input the competitor SKUs you want to convert
        test_skus = ["BD047R", "03-001-00-01"] 
        
        # 3. Execute the search
        result_data = search_competitor_sku(test_skus, token)
        
        if result_data:
            flattened_results = []
            
            for item in result_data:
                search_term = item.get('searchTerm')
                matches = item.get('matches', [])
                
                if not matches:
                    # Record the search term if no match is found
                    flattened_results.append({
                        'Search_Term': search_term, 
                        'Match_Found': False,
                        'Competitor_Manufacturer': None,
                        'Competitor_SKU': None,
                        'KLS_SKU': None,
                        'KLS_Name': None
                    })
                else:
                    for match in matches:
                        # 1. Extract Competitor Metadata
                        comp_prod = match.get('competitorProduct') or {}
                        
                        # Handle potential nesting within the manufacturer attribute
                        mfr_data = comp_prod.get('manufacturer')
                        if isinstance(mfr_data, dict):
                            comp_mfr = mfr_data.get('name')
                        else:
                            comp_mfr = mfr_data
                            
                        comp_sku = comp_prod.get('code') or comp_prod.get('sku') or comp_prod.get('articleNumber')
                        
                        # 2. Extract KLS Martin Matches
                        kls_products = match.get('matchingKlsMartinProducts') or []
                        
                        for kls_prod in kls_products:
                            # Account for product object nesting if present
                            if 'product' in kls_prod and isinstance(kls_prod['product'], dict):
                                target_obj = kls_prod['product']
                            else:
                                target_obj = kls_prod
                                
                            kls_sku = target_obj.get('code') or target_obj.get('sku')
                            
                            # Parse name dict if necessary
                            raw_name = target_obj.get('name')
                            if isinstance(raw_name, dict):
                                kls_name = raw_name.get('value')
                            else:
                                kls_name = raw_name
                            
                            # Append a unique row for every KLS mapping
                            flattened_results.append({
                                'Search_Term': search_term, 
                                'Match_Found': True,
                                'Competitor_Manufacturer': comp_mfr,
                                'Competitor_SKU': comp_sku,
                                'KLS_SKU': kls_sku,
                                'KLS_Name': kls_name
                            })
            
            # Standardize the output into a pandas DataFrame
            df_converted = pd.DataFrame(flattened_results)
            
            print("\nFully Flattened Data Structure:")
            print(df_converted.to_string(index=False))
    else:
        print("Authentication failed. Check credentials or network state.")

df_converted = pd.DataFrame(flattened_results)
df_converted = df_converted.drop(columns=['KLS_Name'])

output_path = r"C:\Users\Anas Mohamed\PyCharmMiscProject\Competitor_Cross_Reference.xlsx"
df_converted.to_excel(output_path, index=False)
print(f"\nMapping table exported successfully to {output_path}")