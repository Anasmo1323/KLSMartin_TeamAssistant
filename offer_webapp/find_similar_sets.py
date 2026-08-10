import pandas as pd
from itertools import combinations

def find_similar_sets():
    outpath = r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\master_surgical_sets.xlsx'
    
    xls = pd.ExcelFile(outpath)
    sheets = xls.sheet_names
    
    set_items = {}
    
    for sheet in sheets:
        df = pd.read_excel(outpath, sheet_name=sheet)
        if 'Article No' in df.columns:
            # Drop na and get unique article numbers
            items = set(df['Article No'].dropna().astype(str).str.strip())
            set_items[sheet] = items
            
    # Compare all pairs
    similar_pairs = []
    
    for s1, s2 in combinations(sheets, 2):
        items1 = set_items.get(s1, set())
        items2 = set_items.get(s2, set())
        
        if not items1 or not items2:
            continue
            
        intersection = items1.intersection(items2)
        union = items1.union(items2)
        
        overlap_1 = len(intersection) / len(items1)
        overlap_2 = len(intersection) / len(items2)
        
        jaccard = len(intersection) / len(union)
        
        # We care if one is a subset of the other, or if they are highly similar (>75% jaccard)
        if jaccard > 0.6 or overlap_1 > 0.8 or overlap_2 > 0.8:
            similar_pairs.append({
                'set1': s1,
                'set2': s2,
                'len1': len(items1),
                'len2': len(items2),
                'intersect': len(intersection),
                'jaccard': jaccard,
                'overlap_1': overlap_1,
                'overlap_2': overlap_2
            })
            
    import json
    with open('similar_sets.json', 'w') as f:
        json.dump(similar_pairs, f, indent=2)
        
    print(f"Found {len(similar_pairs)} potentially similar set pairs.")

if __name__ == '__main__':
    find_similar_sets()
