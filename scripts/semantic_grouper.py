import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import json
import warnings
import torch
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import HDBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from llama_cpp import Llama

warnings.filterwarnings('ignore')

class SemanticGrouper:
    def __init__(self, master_df: pd.DataFrame, model_path: str, cache_dir: str = 'cache'):
        self.master_df = master_df
        self.model_path = model_path
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.llm_cache_path = os.path.join(self.cache_dir, 'llm_cluster_names.json')
        self.embeddings_cache_path = os.path.join(self.cache_dir, 'item_embeddings.pt')
        
        self.llm_cache = self._load_cache(self.llm_cache_path)
        
        self.sentence_model = None
        self.llm = None
        
    def _load_cache(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def _save_cache(self, cache, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
            
    def _get_sentence_model(self):
        if self.sentence_model is None:
            print('Loading SentenceTransformer model...')
            os.environ['HF_HUB_OFFLINE'] = '1'
            try:
                self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', local_files_only=True)
            except:
                os.environ.pop('HF_HUB_OFFLINE', None)
                self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        return self.sentence_model
        
    def _get_llm(self):
        if self.llm is None:
            print(f'Loading LLM from {self.model_path}...')
            self.llm = Llama(model_path=self.model_path, n_ctx=2048, verbose=False, n_threads=4)
            print('LLM Initialized successfully!')
        return self.llm
        
    def generate_embeddings(self, descriptions: list):
        model = self._get_sentence_model()
        print(f'Generating Semantic embeddings for {len(descriptions)} items...')
        
        if os.path.exists(self.embeddings_cache_path):
            try:
                cache_data = torch.load(self.embeddings_cache_path, weights_only=False)
                if len(cache_data['embeddings']) == len(descriptions):
                    semantic_embeddings = cache_data['embeddings'].cpu().numpy()
                    print('Loaded semantic embeddings from cache.')
                    return semantic_embeddings
            except Exception as e:
                print('Failed to load embeddings cache:', e)
                
        semantic_embeddings = model.encode(descriptions, convert_to_tensor=True, show_progress_bar=True).cpu().numpy()
        torch.save({'embeddings': torch.tensor(semantic_embeddings)}, self.embeddings_cache_path)
        
        return semantic_embeddings
        
    def get_cluster_name(self, items: list, cluster_id):
        items_sorted = sorted(items)
        cache_key = '|'.join(items_sorted[:10])
        
        if cache_key in self.llm_cache:
            return self.llm_cache[cache_key]
            
        llm = self._get_llm()
        
        sample = list(np.random.choice(items_sorted, size=min(5, len(items_sorted)), replace=False))
        sample_text = "\n".join([f'- {desc}' for desc in sample])
        
        prompt = f"""<|im_start|>system
You are a medical catalog expert. I will give you a list of 1 to 5 surgical instrument descriptions that belong to the SAME product family.
Your task is to identify the root Family Name (e.g. "Scalpel Handle", "Metzenbaum Scissors", "Adson Forceps").
Extract ONLY the core family name. DO NOT include dimensions, sizes, curves, or specific features.
Respond ONLY with the generalized family name. Nothing else.
<|im_end|>
<|im_start|>user
Descriptions:
{sample_text}
<|im_end|>
<|im_start|>assistant
"""
        try:
            response = llm(prompt, max_tokens=20, stop=['<|im_end|>', '\n'], echo=False)
            family_name = response['choices'][0]['text'].strip()
            
            family_name = family_name.replace('\"', '').strip()
            if not family_name:
                family_name = f'Cluster {cluster_id}'
                
            self.llm_cache[cache_key] = family_name.title()
            self._save_cache(self.llm_cache, self.llm_cache_path)
            
            return self.llm_cache[cache_key]
        except Exception as e:
            print(f'LLM Error: {e}')
            return f'Cluster {cluster_id}'

    def run(self):
        df = self.master_df.copy()
        df['description'] = df['description'].fillna('').astype(str)
        df['brochures'] = df['brochures'].fillna('').astype(str)
        descriptions = (df['description'] + ' ' + df['brochures']).tolist()
        
        sem_emb = self.generate_embeddings(descriptions)
        
        print('Clustering items with HDBSCAN...')
        # Set n_jobs=1 to prevent joblib from spawning processes that deadlock OpenMP/llama.cpp
        clusterer = HDBSCAN(min_cluster_size=3, metric='euclidean', cluster_selection_method='eom', n_jobs=1)
        labels = clusterer.fit_predict(sem_emb)
        
        df['cluster_id'] = labels
        df['best_name'] = ''
        
        unique_clusters = df['cluster_id'].unique()
        print(f'Found {len(unique_clusters)} clusters. Naming them via LLM...')
        
        # Sort cluster sizes to name larger clusters first, gives better progress perception
        cluster_sizes = df.groupby('cluster_id').size().sort_values(ascending=False)
        
        from tqdm import tqdm
        for cid in tqdm(cluster_sizes.index, desc="Naming clusters via LLM"):
            mask = df['cluster_id'] == cid
            cluster_descs = df.loc[mask, 'description'].tolist()
            
            if cid == -1: 
                for idx in df[mask].index:
                    df.at[idx, 'best_name'] = self.get_cluster_name([df.at[idx, 'description']], f'Noise_{idx}')
            else:
                family_name = self.get_cluster_name(cluster_descs, cid)
                df.loc[mask, 'best_name'] = family_name
                
        def extract_modifier(row):
            desc = str(row['description'])
            name = str(row['best_name'])
            import re
            mod = re.sub(re.escape(name), '', desc, flags=re.IGNORECASE).strip(' ,-')
            mod = re.sub(r'[, -]+', ' ', mod).strip()
            return mod if mod else None
            
        df['modifiers'] = df.apply(extract_modifier, axis=1)
        df['family'] = df['best_name']
        
        # Now, since we are returning df_clean in the pipeline, we must set family_id properly for the JSON grouping!
        # JSON grouping uses 'family_id' to separate items. Since semantic clustering finds actual families, we can use the cluster_id as the family_id!
        df['family_id'] = df['cluster_id'].astype(str)
        
        return df
