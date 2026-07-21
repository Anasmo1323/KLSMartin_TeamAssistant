import pandas as pd
import time
from llama_cpp import Llama
import os
from tqdm import tqdm

print("Loading LLM model (Qwen 2 7B)...")
try:
    llm = Llama(
        model_path="models/qwen2-7b-instruct-q4_k_m.gguf",
        n_gpu_layers=-1,
        n_ctx=1024,
        verbose=False
    )
    print("Model successfully loaded!")
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

system_msg = """You are an expert medical catalog assistant. 
Your task is to read the description of a surgical instrument and extract ONLY its core Family Name.
Rules:
1. Strip out all physical variations (length, curved, straight, fine, blunt, ratchet, teeth, mm, cm).
2. KEEP important designators like 'acc. to [Name]' or specific model names (e.g. 'Adson', 'Mayo').
3. DO NOT output any extra text, only the extracted family name.
"""

file_name = "KLS_All_Products.xlsx"
save_name = "KLS_All_Products_AI.xlsx"

desc_cache = {}

if os.path.exists(save_name):
    print(f"Found existing {save_name}. Resuming progress...")
    df = pd.read_excel(save_name)
    
    # Pre-load cache with already processed items
    for idx, row in df.iterrows():
        fam = str(row.get('Family', ''))
        desc = str(row.get('description', ''))
        if pd.notna(fam) and fam.strip() != "" and fam.strip().lower() != "nan":
            desc_cache[desc] = fam
else:
    print(f"Loading {file_name}...")
    df = pd.read_excel(file_name)
    # Clear the existing family column so the AI processes everything from scratch
    df['Family'] = ""

col_map = {str(c).lower().strip(): c for c in df.columns}
desc_col = col_map.get('description')

if not desc_col:
    print("Error: Could not find 'description' column.")
    exit(1)

total_items = len(df)
processed_count = 0

print("\nStarting AI processing...")
# Use tqdm for a beautiful progress bar
with tqdm(total=total_items, desc="Generating Families", unit="item") as pbar:
    for idx, row in df.iterrows():
        # Check if already processed (from resume)
        fam_val = row['Family']
        if pd.notna(fam_val) and str(fam_val).strip() != "" and str(fam_val).strip().lower() != "nan":
            pbar.update(1)
            continue
            
        desc = str(row[desc_col])
        if pd.isna(desc) or not desc.strip() or desc.lower() == "nan":
            pbar.update(1)
            continue
            
        # Fast path: already inferred this identical description
        if desc in desc_cache:
            df.at[idx, 'Family'] = desc_cache[desc]
            pbar.update(1)
            continue
            
        # Query LLM
        try:
            response = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"Description: {desc}\nFamily Name:"}
                ],
                temperature=0.0,
                max_tokens=40
            )
            
            family_name = response['choices'][0]['message']['content'].strip()
            
            # Cleanup potential AI conversational junk
            if family_name.lower().startswith("family name:"):
                family_name = family_name[12:].strip()
                
            df.at[idx, 'Family'] = family_name
            desc_cache[desc] = family_name
            
        except Exception as e:
            tqdm.write(f"Error processing row {idx}: {e}")
            
        processed_count += 1
        pbar.update(1)
        
        # Auto-Save every 50 unique inference calls
        if processed_count % 50 == 0:
            df.to_excel(save_name, index=False)

# Final save
print("\nProcessing complete! Final save...")
df.to_excel(save_name, index=False)
print(f"Finished! Your AI-processed file is saved as {save_name}.")
