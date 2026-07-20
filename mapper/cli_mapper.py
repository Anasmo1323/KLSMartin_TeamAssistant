import os
os.environ['HF_HUB_OFFLINE'] = '1'

import sys
import json
import pandas as pd
from llama_cpp import Llama
from mapper import AIEngine
from core.utils import resource_path
import warnings
warnings.filterwarnings('ignore')

def main():
    print("=========================================")
    print("      KLS Martin CLI Mapper Testing      ")
    print("=========================================")
    
    # 1. Load Master Data
    print("\n[1/3] Loading Master Database...")
    master_path = resource_path("KLS_All_Products.xlsx")
    if not os.path.exists(master_path):
        print(f"ERROR: Master file not found at {master_path}")
        return
        
    master_df = pd.read_excel(master_path, dtype=str).fillna("")
    print(f"Loaded {len(master_df)} items.")
    
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # 2. Initialize Hybrid Search Engine
    print("\n[2/3] Initializing Hybrid Search Engine (SentenceTransformers & TF-IDF)...")
    ai_engine = AIEngine(master_df)
    print("Loading embeddings (this may take a moment if not cached)...")
    ai_engine.run()
    
    if ai_engine.corpus_embeddings is None:
        print("\nFATAL ERROR: Failed to load embeddings or hybrid search engine!")
        print("Check the errors above (e.g. internet connection issues).")
        return
    
    # 3. Initialize LLM
    print("\n[3/3] Initializing Qwen2-7B LLM (This takes ~30 seconds)...")
    model_path = resource_path("models/qwen2-7b-instruct-q4_k_m.gguf")
    if not os.path.exists(model_path):
        print(f"ERROR: LLM model not found at {model_path}")
        return
        
    try:
        llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
        print("LLM Loaded successfully!")
    except Exception as e:
        print(f"ERROR initializing LLM: {e}")
        return

    print("\n=========================================")
    print("System Ready! Type 'exit' to quit.")
    print("=========================================")
    
    while True:
        query = input("\nEnter medical instrument name (or 'exit'): ").strip()
        if not query:
            continue
        if query.lower() in ['exit', 'quit']:
            break
            
        print("\n--- [Stage 1/3] LLM Pre-Translating Arabic to English ---")
        translate_prompt = f"""<|im_start|>system
You are an expert medical translator. Translate the following Arabic medical instrument name or description into a clean, precise English medical term. Do not add any explanations or notes, just output the English translation.
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""
        try:
            trans_response = llm(translate_prompt, max_tokens=50, stop=["<|im_end|>"], echo=False)
            english_query = trans_response['choices'][0]['text'].strip()
            print(f"Translation: '{english_query}'")
        except Exception as e:
            print(f"Translation Error: {e}")
            continue
            
        print(f"\n--- [Stage 2/3] Hybrid Search for: '{english_query}' ---")
        candidates = ai_engine.find_top_matches(english_query, top_k=15)
        
        candidates_text = ""
        for i, c in enumerate(candidates):
            candidates_text += f"Code: {c['code']} - Description: {c['description']}\n"
            if i < 3: # Only print top 3 to console so we don't flood it
                print(f"  {i+1}. {c['code']} (Score: {c['score']:.2f}) -> {c['description'][:60]}...")
                
        print(f"  ... (passing all {len(candidates)} to LLM)")
        
        print("\n--- [Stage 3/3] LLM Reasoning ---")
        prompt = f"""<|im_start|>system
You are a precise medical data extraction assistant. You will be given a raw medical instrument order list item, and a list of 15 candidate products from the KLS Martin catalog.
Your task is to identify the best matching product from the candidate list, even if it's an approximate match based on medical slang, abbreviations, or partial names.
You must reply ONLY in valid JSON format: {{"best_match_code": "the_code"}} or {{"best_match_code": null}} if absolutely none are a good match.
Do not output anything else. No explanations.
<|im_end|>
<|im_start|>user
Original Item: {query}
Translated Item: {english_query}

Candidates:
{candidates_text}
<|im_end|>
<|im_start|>assistant
"""
        try:
            response = llm(prompt, max_tokens=100, stop=["<|im_end|>"], echo=False)
            text_result = response['choices'][0]['text'].strip()
            print(f"Raw LLM Output: {text_result}")
            
            import re
            json_match = re.search(r'\{.*?\}', text_result, re.DOTALL)
            if json_match:
                result_dict = json.loads(json_match.group())
                best_code = result_dict.get('best_match_code')
                if best_code:
                    print(f"\n>> SUCCESS! LLM chose KLS Code: {best_code}")
                else:
                    print("\n>> LLM concluded there is no confident match.")
            else:
                print("\n>> ERROR: LLM did not return JSON.")
                
        except Exception as e:
            print(f"\n>> LLM INFERENCE ERROR: {e}")

if __name__ == "__main__":
    main()
