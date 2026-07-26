import os
import ast
import requests
import pandas as pd
import urllib3
from playwright.sync_api import sync_playwright

# Suppress insecure request warnings caused by bypassing SSL validation
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_clean_value(val):
    """Recursively extract string values from nested dictionaries or list structures."""
    if val is None:
        return ""
    if isinstance(val, dict):
        if 'value' in val:
            return extract_clean_value(val['value'])
        if 'name' in val:
            return extract_clean_value(val['name'])
        if 'title' in val:
            return extract_clean_value(val['title'])
        # Fallback if dictionary has unknown keys
        return str(val)
    if isinstance(val, str) and val.startswith('{'):
        try:
            parsed = ast.literal_eval(val)
            return extract_clean_value(parsed)
        except Exception:
            return val
    if isinstance(val, list):
        return ", ".join([str(extract_clean_value(item)) for item in val if item is not None])
    return val

def scrape_alma_sets():
    # 1. Configuration
    EMAIL = "albear@technowave-eg.com"
    PASSWORD = "KLSteam@123"
    LOGIN_URL = "https://alma.klsmartin.com/kls-library/sets"
    TARGET_SETS_API_URL = "https://alma.klsmartin.com/api/backend/Set/list?PageSize=-1" 

    api_response_data = None
    auth_token = None

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

        print("Navigating to ALMA sets portal...")
        page.goto(LOGIN_URL)

        print("Executing authentication flow...")
        page.wait_for_selector('input[placeholder="Email *"]')
        page.fill('input[placeholder="Email *"]', EMAIL)
        page.click('button:has-text("Login / Sign up")')

        page.wait_for_selector('input[type="password"]', timeout=15000)
        page.fill('input[type="password"]', PASSWORD)
        page.click('button[type="submit"], button#next')

        print("Waiting for session initialization...")
        page.wait_for_load_state("networkidle", timeout=30000)

        if not auth_token:
            print("Error: Could not capture Authorization token.")
            browser.close()
            return

        print("Executing bulk Sets metadata request...")
        api_response = page.request.get(
            TARGET_SETS_API_URL, 
            headers={"Authorization": auth_token, "Accept": "application/json"}
        )

        if api_response.ok:
            api_response_data = api_response.json()
        else:
            print(f"API Request Failed. HTTP Status: {api_response.status}")
            browser.close()
            return

        browser.close()

    # 2. Extract Master Sets List
    if api_response_data:
        if isinstance(api_response_data, dict) and 'items' in api_response_data:
            sets_list = api_response_data['items']
        elif isinstance(api_response_data, dict) and 'data' in api_response_data:
            sets_list = api_response_data['data']
        else:
            sets_list = api_response_data

        if sets_list and len(sets_list) > 0:
            print(f"\n[DEBUG] Inspected First Set Payload Keys: {list(sets_list[0].keys())}\n")

        flattened_data = []
        req_headers = {
            "Authorization": auth_token,
            "Accept": "application/json"
        }

        print(f"Discovered {len(sets_list)} sets. Extracting nested components...")

        # 3. Two-Tier Iteration
        for index, s in enumerate(sets_list):
            # Attempt multi-key resolution for Set ID and Set Code
            set_id = s.get('id') or s.get('setId') or s.get('uuid') or s.get('key')
            set_code = s.get('code') or s.get('number') or s.get('sku') or s.get('setNumber') or s.get('setNo')

            base_info = {
                'Set_ID': set_id,
                'Set_Code': set_code,
                'Set_Name': extract_clean_value(s.get('name')),
                'Set_Type': extract_clean_value(s.get('type')),
                'Discipline': extract_clean_value(s.get('discipline') or s.get('disciplines')),
                'Region': extract_clean_value(s.get('region') or s.get('regions')),
                'Set_State': 'Active' if str(s.get('enabled')).lower() == 'true' else 'Inactive'
            }

            if not set_id:
                # If set_id is still missing, attempt fetching using set_code as fallback parameter
                set_id = set_code

            if not set_id:
                flattened_data.append(base_info)
                continue

            # Query the secondary items list endpoint
            items_endpoint = f"https://alma.klsmartin.com/api/backend/Set/{set_id}/items/list?PageSize=-1"
            
            try:
                res = requests.get(items_endpoint, headers=req_headers, verify=False, timeout=15)
                
                if res.status_code == 200:
                    items_data = res.json()
                    
                    if isinstance(items_data, dict):
                        nested_items = items_data.get('items') or items_data.get('data') or []
                    elif isinstance(items_data, list):
                        nested_items = items_data
                    else:
                        nested_items = []

                    if not nested_items:
                        row = base_info.copy()
                        row.update({'Item_SKU': None, 'Item_Name': None, 'Quantity': None, 'Author': None})
                        flattened_data.append(row)
                    else:
                        for item in nested_items:
                            row = base_info.copy()
                            prod_obj = item.get('product') if isinstance(item.get('product'), dict) else {}
                            
                            row['Item_SKU'] = item.get('sku') or item.get('code') or prod_obj.get('sku') or prod_obj.get('code')
                            row['Item_Name'] = extract_clean_value(item.get('name') or prod_obj.get('name'))
                            row['Quantity'] = item.get('quantity')
                            row['Author'] = extract_clean_value(item.get('author') or prod_obj.get('author'))
                            
                            flattened_data.append(row)
                else:
                    print(f"Failed to fetch items for Set {base_info['Set_Code']} (ID: {set_id}). Status: {res.status_code}")
                    flattened_data.append(base_info)

            except Exception as e:
                print(f"Error requesting items for Set {base_info['Set_Code']}: {e}")
                flattened_data.append(base_info)

            if (index + 1) % 25 == 0:
                print(f"Processed {index + 1}/{len(sets_list)} sets...")

        # 4. Generate Final Export
        df = pd.DataFrame(flattened_data)
        
        # Ensure optimal column order in output
        column_order = [
            'Set_ID', 'Set_Code', 'Set_Name', 'Set_Type', 'Discipline', 'Region', 'Set_State',
            'Item_SKU', 'Item_Name', 'Quantity', 'Author'
        ]
        
        # Keep only existing columns that match
        final_cols = [col for col in column_order if col in df.columns]
        df = df[final_cols]

        output_file = "ALMA_Sets_Export.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\nPipeline complete. Exported {len(df)} total component rows to {output_file}.")

    else:
        print("Pipeline aborted due to empty master sets payload.")

if __name__ == '__main__':
    scrape_alma_sets()