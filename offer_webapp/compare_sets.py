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
        for val in row.values:
            val_str = str(val).strip()
            if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', val_str):
                art_no = val_str
                break
        if art_no:
            try:
                qty = float(row.iloc[qty_col_idx])
            except:
                qty = 1.0
            items[art_no] = items.get(art_no, 0) + qty
    return items

def get_gcd(values):
    int_vals = [int(v) for v in values if v > 0]
    if not int_vals:
        return 1
    return reduce(math.gcd, int_vals)

def analyze():
    dir_path = r'C:\Users\Anas Mohamed\PyCharmMiscProject\SurgicalSets'
    
    a1_path = dir_path + r'\A1 Sets in details.xlsx'
    a2_path = r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\src\data\A2_parsed_sets.json'
    a3_path = dir_path + r'\A3 sets.xlsx'
    
    sets_data = {} 
    
    # Process A1
    xls_a1 = pd.ExcelFile(a1_path)
    for sheet in xls_a1.sheet_names:
        df = pd.read_excel(a1_path, sheet_name=sheet)
        cname = clean_name(sheet)
        if cname not in sets_data:
            sets_data[cname] = {'name': sheet}
        
        items = {}
        for _, row in df.iterrows():
            art_no = ""
            for val in row.values:
                val_str = str(val).strip()
                if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', val_str):
                    art_no = val_str
                    break
            if art_no:
                try:
                    qty = float(row.iloc[3])
                except:
                    qty = 1.0
                items[art_no] = items.get(art_no, 0) + qty
        sets_data[cname]['A1'] = items

    # Process A2
    with open(a2_path, 'r', encoding='utf-8') as f:
        a2_json = json.load(f)
        for s in a2_json:
            cname = clean_name(s['set_name'])
            if cname not in sets_data:
                sets_data[cname] = {'name': s['set_name']}
            items = {}
            for item in s['items']:
                items[item['art_no']] = items.get(item['art_no'], 0) + float(item['qty'])
            sets_data[cname]['A2'] = items
            
    # Process A3
    xls_a3 = pd.ExcelFile(a3_path)
    for sheet in xls_a3.sheet_names:
        df = pd.read_excel(a3_path, sheet_name=sheet)
        cname = clean_name(sheet)
        if cname not in sets_data:
            sets_data[cname] = {'name': sheet}
        items = {}
        for _, row in df.iterrows():
            art_no = ""
            for val in row.values:
                val_str = str(val).strip()
                if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', val_str):
                    art_no = val_str
                    break
            if art_no:
                try:
                    qty = float(row.iloc[5])
                except:
                    qty = 1.0
                items[art_no] = items.get(art_no, 0) + qty
        sets_data[cname]['A3'] = items
        
    # Process Demerdash
    demerdash_path = dir_path + r'\Demerdash Order - PO final.xlsx'
    df_d = pd.read_excel(demerdash_path, sheet_name='PO (2)', header=None)
    current_set = None
    for _, row in df_d.iterrows():
        art_no = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
        
        if re.search(r'\d{2}-\d{3}-\d{2}-\d{2}', art_no):
            if current_set:
                try:
                    qty = float(row.iloc[3])
                except:
                    qty = 1.0
                sets_data[current_set]['Demerdash'][art_no] = sets_data[current_set]['Demerdash'].get(art_no, 0) + qty
        elif desc and desc.lower() != 'nan' and desc.lower() != 'description' and not desc.startswith('Tray Name'):
            cname = clean_name(desc)
            if cname not in sets_data:
                sets_data[cname] = {'name': desc}
            if 'Demerdash' not in sets_data[cname]:
                sets_data[cname]['Demerdash'] = {}
            current_set = cname
            
    # Generate report
    with open('set_differences_report.md', 'w', encoding='utf-8') as out:
        out.write("# Surgical Sets Comparison Report (A1 vs A2 vs A3 vs Demerdash)\n\n")
        out.write("This report details the TRUE content differences (items per set) ignoring the total order quantities.\n\n")
        
        for cname, data in sets_data.items():
            a1_items = data.get('A1', {})
            a2_items = data.get('A2', {})
            a3_items = data.get('A3', {})
            dem_items = data.get('Demerdash', {})
            
            sources_present = []
            if a1_items: sources_present.append('A1')
            if a2_items: sources_present.append('A2')
            if a3_items: sources_present.append('A3')
            if dem_items: sources_present.append('Demerdash')
            
            if len(sources_present) > 1:
                # Normalize quantities by dividing by GCD
                a1_gcd = get_gcd(a1_items.values()) if a1_items else 1
                a2_gcd = get_gcd(a2_items.values()) if a2_items else 1
                a3_gcd = get_gcd(a3_items.values()) if a3_items else 1
                dem_gcd = get_gcd(dem_items.values()) if dem_items else 1
                
                out.write(f"## Set: `{data['name']}` ({cname})\n")
                out.write(f"Present in: {', '.join(sources_present)}\n")
                out.write(f"*Inferred Number of Sets Ordered: ")
                multipliers = []
                if 'A1' in sources_present: multipliers.append(f"A1={a1_gcd}")
                if 'A2' in sources_present: multipliers.append(f"A2={a2_gcd}")
                if 'A3' in sources_present: multipliers.append(f"A3={a3_gcd}")
                if 'Demerdash' in sources_present: multipliers.append(f"Demerdash={dem_gcd}")
                out.write(", ".join(multipliers) + "*\n\n")
                
                all_codes = set(a1_items.keys()) | set(a2_items.keys()) | set(a3_items.keys()) | set(dem_items.keys())
                
                out.write("| Article No |")
                if 'A1' in sources_present: out.write(" Items/Set (A1) |")
                if 'A2' in sources_present: out.write(" Items/Set (A2) |")
                if 'A3' in sources_present: out.write(" Items/Set (A3) |")
                if 'Demerdash' in sources_present: out.write(" Items/Set (Demerdash) |")
                out.write(" Content Match |\n")
                
                out.write("|---|")
                if 'A1' in sources_present: out.write("---|")
                if 'A2' in sources_present: out.write("---|")
                if 'A3' in sources_present: out.write("---|")
                if 'Demerdash' in sources_present: out.write("---|")
                out.write("---|\n")
                
                differences_found = False
                
                for code in sorted(list(all_codes)):
                    # Get normalized quantity per set
                    q1 = int(a1_items.get(code, 0) / a1_gcd) if 'A1' in sources_present else None
                    q2 = int(a2_items.get(code, 0) / a2_gcd) if 'A2' in sources_present else None
                    q3 = int(a3_items.get(code, 0) / a3_gcd) if 'A3' in sources_present else None
                    qd = int(dem_items.get(code, 0) / dem_gcd) if 'Demerdash' in sources_present else None
                    
                    qs = []
                    if q1 is not None: qs.append(q1)
                    if q2 is not None: qs.append(q2)
                    if q3 is not None: qs.append(q3)
                    if qd is not None: qs.append(qd)
                    
                    if len(set(qs)) == 1:
                        status = "✅ Match"
                    elif 0 in qs:
                        status = "⚠️ Missing Item"
                        differences_found = True
                    else:
                        status = "❌ Qty Mismatch"
                        differences_found = True
                        
                    out.write(f"| `{code}` |")
                    if 'A1' in sources_present: out.write(f" {q1 if q1 is not None else '-'} |")
                    if 'A2' in sources_present: out.write(f" {q2 if q2 is not None else '-'} |")
                    if 'A3' in sources_present: out.write(f" {q3 if q3 is not None else '-'} |")
                    if 'Demerdash' in sources_present: out.write(f" {qd if qd is not None else '-'} |")
                    out.write(f" {status} |\n")
                
                if not differences_found:
                    out.write("\n**Summary:** Content is exactly identical across all sources! No items are missing or differ in per-set quantity.\n\n")
                else:
                    out.write("\n**Summary:** True content differences found (missing items or differing quantities per set).\n\n")

if __name__ == '__main__':
    analyze()
