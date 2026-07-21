import pandas as pd
import re
from collections import defaultdict

print("Loading KLS_All_Products.xlsx...")
df = pd.read_excel("KLS_All_Products.xlsx")

# Ensure required columns exist
# Keep original column names to preserve user's formatting, but create a lower map
col_map = {str(c).lower().strip(): c for c in df.columns}

if 'code' not in col_map or 'description' not in col_map:
    print("Error: Missing 'code' or 'description' columns.")
    exit(1)

code_col = col_map['code']
desc_col = col_map['description']

# Ensure 'family' column exists
if 'family' not in col_map:
    # Add Family right after Description
    desc_idx = df.columns.get_loc(desc_col)
    df.insert(desc_idx + 1, 'Family', "")
    family_col = 'Family'
else:
    family_col = col_map['family']

# Bucket by first code segment (e.g., "11-100-14-07" -> "11")
print("Bucketing items...")
buckets = defaultdict(list)
for idx, row in df.iterrows():
    code = str(row[code_col])
    parts = code.split('-')
    bucket_key = parts[0] if len(parts) > 0 else code
    buckets[bucket_key].append(idx)

print(f"Created {len(buckets)} buckets.")

# Process each bucket
print("Clustering and computing common strings...")
for bucket_key, indices in buckets.items():
    clusters = []
    
    for idx in indices:
        desc = str(df.at[idx, desc_col])
        if pd.isna(desc) or not desc.strip() or desc == "nan":
            continue
            
        placed = False
        for cluster in clusters:
            ref_idx = cluster[0]
            ref_desc = str(df.at[ref_idx, desc_col])
            
            # String similarity check
            min_len = min(len(ref_desc), len(desc))
            common = ""
            for i in range(min_len):
                if ref_desc[i] != desc[i]:
                    break
                common += ref_desc[i]
                
            part1 = ref_desc.split(',')[0].strip()
            if not part1: part1 = ref_desc
            
            if common.startswith(part1) and len(common) >= len(part1):
                cluster.append(idx)
                placed = True
                break
                
        if not placed:
            clusters.append([idx])
            
    # Compute longest common string for each cluster
    for cluster in clusters:
        if len(cluster) > 1:
            descs = [str(df.at[idx, desc_col]) for idx in cluster]
            s1, s2 = min(descs), max(descs)
            common = ""
            for i, c in enumerate(s1):
                if c != s2[i]:
                    common = s1[:i]
                    break
            else:
                common = s1
            family_name = common.strip(" ,;")
        else:
            # Single item in cluster
            desc = str(df.at[cluster[0], desc_col])
            parts = [p.strip() for p in desc.split(',')]
            if len(parts) > 1:
                part2 = parts[1].lower()
                var_pattern = r'\b(blunt|pointed|fine|straight|curved|length|mm|cm|inch|teeth|serrated|hollow|solid|delicate|strong|wide|narrow|x)\b'
                is_variation = bool(re.search(var_pattern, part2))
                if "acc." in part2 or "acc " in part2:
                    is_variation = False
                family_name = parts[0] if is_variation else f"{parts[0]}, {parts[1]}"
            else:
                family_name = desc
                
        # Assign to dataframe
        for idx in cluster:
            current_family = str(df.at[idx, family_col])
            if pd.isna(current_family) or current_family == "nan" or current_family.strip() == "":
                df.at[idx, family_col] = family_name

print("Saving to KLS_All_Products_Updated.xlsx...")
df.to_excel("KLS_All_Products_Updated.xlsx", index=False)
print("Complete!")
