import pandas as pd
import json
import re
import math
from functools import reduce

def clean_name(name):
    name = re.sub(r'^\d+\.', '', name)
    name = re.sub(r'\(.*?\)', '', name)
    words_to_remove = ['set', 'surgery', 'instrument', 'instruments', 'product', 'surgical', 'for', 'basic']
    name = name.lower().strip()
    parts = re.findall(r'\w+', name)
    filtered = [p for p in parts if p not in words_to_remove]
    return ' '.join(filtered).strip()

def get_items_from_df(df, art_no_col_idx, qty_col_idx):
    items = {}
    for _, row in df.iterrows():
        art_no = ""
        description = ""
        # Look for ArtNo
        for val in row.values:
            val_str = str(val).strip()
            if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', val_str):
                art_no = val_str
                break
        
        # Look for Description (usually the longest string in the row that's not ArtNo)
        # Or just pick the column after ArtNo if possible. We'll just grab the first non-numeric long string.
        desc_candidates = []
        for val in row.values:
            val_str = str(val).strip()
            if val_str and val_str != art_no and not val_str.replace('.', '', 1).isdigit() and val_str.lower() != 'nan':
                desc_candidates.append(val_str)
        if desc_candidates:
            description = max(desc_candidates, key=len) # longest string is usually description
            
        if art_no:
            try:
                qty = float(row.iloc[qty_col_idx])
            except:
                qty = 1.0
            
            if art_no in items:
                items[art_no]['qty'] += qty
            else:
                items[art_no] = {'qty': qty, 'description': description}
    return items

def get_gcd(values):
    int_vals = [int(v) for v in values if v > 0]
    if not int_vals:
        return 1
    return reduce(math.gcd, int_vals)

def get_canonical_name(name):
    n = name.lower()
    
    if 'extra vascular' in n: return '4. Extra Vascular Pediatric Set'
    
    if 'general plastic' in n: return '10. General Plastic Surgical Instruments'
    
    if 'basic instr' in n: return '11. Basic Instruments For Plastic & Reconstructive Surgery'
    
    if 'applying forceps' in n or 'micro instr' in n or 'micro sur' in n: return '12. Micro Instruments'
    
    if 'maxillofac' in n and 'surg' in n: return '13. Maxillofacial Surgical Instruments'
    if 'maxillofacial' in n and 'set' in n: return '14. Maxillofacial Instrument Sets'
    
    if 'cleft' in n and 'lip' in n: return '15. Cleft Lip & Palate Instrument Set'
    
    if 'craniofacial' in n: return '16. Craniofacial Suspension Set'
    
    if 'septum' in n: return '19. Set for Septum & Nasal Surgery'
    
    if 'vascular' in n and 'renal' in n: return '25. Basic Vascular Renal Transplant'
    
    return clean_name(name)

def generate_master():
    dir_path = r'C:\Users\Anas Mohamed\PyCharmMiscProject\SurgicalSets'
    
    a1_path = dir_path + r'\A1 Sets in details.xlsx'
    a2_path = r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\src\data\A2_parsed_sets.json'
    a3_path = dir_path + r'\A3 sets.xlsx'
    
    sets_data = {} 
    
    # Process A1
    xls_a1 = pd.ExcelFile(a1_path)
    for sheet in xls_a1.sheet_names:
        df = pd.read_excel(a1_path, sheet_name=sheet)
        cname = get_canonical_name(sheet)
        if cname not in sets_data:
            sets_data[cname] = {'name': sheet, 'sources': {}}
        elif len(sheet) > len(sets_data[cname]['name']):
            sets_data[cname]['name'] = sheet
        sets_data[cname]['sources']['A1'] = get_items_from_df(df, 0, 3)

    # Process A2
    with open(a2_path, 'r', encoding='utf-8') as f:
        a2_json = json.load(f)
        for s in a2_json:
            cname = get_canonical_name(s['set_name'])
            if cname not in sets_data:
                sets_data[cname] = {'name': s['set_name'], 'sources': {}}
            elif len(s['set_name']) > len(sets_data[cname]['name']):
                sets_data[cname]['name'] = s['set_name']
                
            items = {}
            for item in s['items']:
                art_no = item['art_no']
                qty = float(item['qty'])
                if art_no in items:
                    items[art_no]['qty'] += qty
                else:
                    items[art_no] = {'qty': qty, 'description': item['description']}
            
            if 'A2' not in sets_data[cname]['sources']:
                sets_data[cname]['sources']['A2'] = {}
            # Merge items if canonical name matched an existing set
            for art_no, item_data in items.items():
                if art_no in sets_data[cname]['sources']['A2']:
                    sets_data[cname]['sources']['A2'][art_no]['qty'] += item_data['qty']
                else:
                    sets_data[cname]['sources']['A2'][art_no] = item_data
            
    # Process A3
    xls_a3 = pd.ExcelFile(a3_path)
    for sheet in xls_a3.sheet_names:
        df = pd.read_excel(a3_path, sheet_name=sheet)
        cname = get_canonical_name(sheet)
        if cname not in sets_data:
            sets_data[cname] = {'name': sheet, 'sources': {}}
        elif len(sheet) > len(sets_data[cname]['name']):
            sets_data[cname]['name'] = sheet
            
        if 'A3' not in sets_data[cname]['sources']:
            sets_data[cname]['sources']['A3'] = {}
            
        items = get_items_from_df(df, 0, 5)
        for art_no, item_data in items.items():
            if art_no in sets_data[cname]['sources']['A3']:
                sets_data[cname]['sources']['A3'][art_no]['qty'] += item_data['qty']
            else:
                sets_data[cname]['sources']['A3'][art_no] = item_data
        
    # Process Demerdash
    demerdash_path = dir_path + r'\Demerdash Order - PO final.xlsx'
    df_d = pd.read_excel(demerdash_path, sheet_name='PO (2)', header=None)
    current_set = None
    for _, row in df_d.iterrows():
        art_no = ""
        description = ""
        for val in row.values:
            val_str = str(val).strip()
            if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', val_str):
                art_no = val_str
                break
                
        desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
        
        if art_no:
            if current_set:
                try:
                    qty = float(row.iloc[3])
                except:
                    qty = 1.0
                if art_no in sets_data[current_set]['sources']['Demerdash']:
                    sets_data[current_set]['sources']['Demerdash'][art_no]['qty'] += qty
                else:
                    sets_data[current_set]['sources']['Demerdash'][art_no] = {'qty': qty, 'description': desc}
        elif desc and desc.lower() != 'nan' and desc.lower() != 'description' and not desc.startswith('Tray Name'):
            cname = get_canonical_name(desc)
            # Only change current_set if it's a known set from A1/A2/A3, OR explicitly has 'set', 'surg', 'instr' in the name
            # This prevents treating sub-headings like "BARD PARKER HANDLE" as entirely new sets
            is_valid_set = cname in sets_data or any(kw in desc.lower() for kw in ['set', 'surg', 'instr'])
            
            if is_valid_set:
                if cname not in sets_data:
                    sets_data[cname] = {'name': desc, 'sources': {}}
                elif len(desc) > len(sets_data[cname]['name']):
                    sets_data[cname]['name'] = desc
                    
                if 'Demerdash' not in sets_data[cname]['sources']:
                    sets_data[cname]['sources']['Demerdash'] = {}
                current_set = cname
            
    # --- POST PROCESSING: Clean up Demerdash Anal Set ---
    brain_keys = [k for k in sets_data.keys() if '22' in k and 'brain' in k]
    lumber_keys = [k for k in sets_data.keys() if '23' in k and 'lumber' in k]
    urology_keys = [k for k in sets_data.keys() if '24' in k and 'urology' in k]
    anal_keys = [k for k in sets_data.keys() if '21' in k and 'anal' in k]
    
    exclude_artnos = set()
    for keys in [brain_keys, lumber_keys, urology_keys]:
        for k in keys:
            for source, items in sets_data[k]['sources'].items():
                exclude_artnos.update(items.keys())
                
    for ak in anal_keys:
        if 'Demerdash' in sets_data[ak]['sources']:
            dem_items = sets_data[ak]['sources']['Demerdash']
            cleaned_items = {k: v for k, v in dem_items.items() if k not in exclude_artnos}
            sets_data[ak]['sources']['Demerdash'] = cleaned_items
            
    # Remove any empty sets
    sets_data = {k: v for k, v in sets_data.items() if any(len(items) > 0 for items in v['sources'].values())}
    
    # Sort sets logically (extract original number if exists, else put at the end)
    def sort_key(item):
        name = item[1]['name']
        match = re.search(r'^(\d+)', name)
        if match:
            return (0, int(match.group(1)), name)
        return (1, 0, name)
        
    sorted_sets = sorted(sets_data.items(), key=sort_key)
    
    outpath = r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\master_surgical_sets.xlsx'
    
    with pd.ExcelWriter(outpath, engine='openpyxl') as writer:
        for idx, (cname, data) in enumerate(sorted_sets, 1):
            master_items = {}
            
            for source, items in data['sources'].items():
                if not items:
                    continue
                gcd = get_gcd([v['qty'] for v in items.values()])
                for art_no, item_data in items.items():
                    norm_qty = int(item_data['qty'] / gcd)
                    if art_no not in master_items:
                        master_items[art_no] = {
                            'Article No': art_no,
                            'Description': item_data['description'],
                            'Qty': norm_qty
                        }
                    else:
                        master_items[art_no]['Qty'] = max(master_items[art_no]['Qty'], norm_qty)
                        if len(item_data['description']) > len(master_items[art_no]['Description']):
                            master_items[art_no]['Description'] = item_data['description']
                            
            if not master_items:
                continue
                
            df_master = pd.DataFrame(list(master_items.values()))
            
            # Format the display name cleanly
            clean_display_name = data['name']
            clean_display_name = re.sub(r'^\d+[\.\s-]*', '', clean_display_name) # strip leading numbers
            clean_display_name = re.sub(r'\(.*?\)', '', clean_display_name) # strip brackets
            clean_display_name = clean_display_name.strip(' .-_')
            if not clean_display_name.lower().endswith('set') and not clean_display_name.lower().endswith('surgery'):
                clean_display_name += ' Set'
            clean_display_name = clean_display_name.title()
            
            # Final numbered name
            final_name = f"{idx}. {clean_display_name}"
            
            # Excel sheet names max 31 characters
            safe_name = re.sub(r'[\\/*?:"<>|]', '', final_name)[:31]
            
            sheet_name = safe_name
            counter = 1
            while sheet_name in writer.sheets:
                suffix = f"_{counter}"
                sheet_name = safe_name[:31-len(suffix)] + suffix
                counter += 1
                
            # Write dataframe starting at row 1 (so row 0 is left empty for our header)
            df_master.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
            
            # Access the worksheet to write the full un-truncated title
            worksheet = writer.sheets[sheet_name]
            
            # Write title in row 1, column 2 (which is the 'Description' column, i.e., 'B1')
            header_cell = worksheet.cell(row=1, column=2, value=final_name)
            
            # Make the title bold
            from openpyxl.styles import Font
            header_cell.font = Font(bold=True, size=12)
            
    print(f"Master file saved to {outpath}")

if __name__ == '__main__':
    generate_master()
