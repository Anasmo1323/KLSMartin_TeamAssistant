# KLSMartin Team Assistant (Technowave Inventory Control Terminal)

A comprehensive inventory control, verification, and AI-powered product mapping assistant built with PyQt6. Designed specifically to handle large equipment catalogs, automate data matching, and streamline stock verification.

## 🚀 Key Features

### 1. KLS Master Catalog 
- **Dynamic Product Browsing**: Fast, responsive data tables to navigate massive product lists seamlessly.
- **Advanced Filtering**: Filter products by multiple specific Categories or Brochures.
- **Search Capabilities**:
  - *Global Search*: Full-text search across all descriptions and data fields.
  - *Segmented Code Search*: Smartly parse and locate precise product codes.
- **Offers Manager**: Quickly build, review, and manage lists of items as an "Offer", and easily export/copy them.
- **One-Click Updates**: Readily upload new master catalog files (`KLS_All_Products.xlsx`) overwriting the old database instantly.

### 2. Intelligent AI Mapper 
- **Hybrid Semantic Search engine**: Blends AI sentence embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) with TF-IDF keyword searching (70% Semantic / 30% Keyword) to match vague Arabic or English descriptions to exact KLS codes.
- **Local LLM Integration**: Uses local GGUF models (e.g. `qwen2-7b-instruct`) completely offline to infer and parse exact matches intelligently.
- **Local Memory**: Saves user-confirmed mappings into a local SQLite database (`mapping_memory.db`) so the system learns your vocabulary over time.
- **Suggestion Dialogs**: Provides intelligent UI popups listing top candidate matches when an exact item isn't immediately found.

### 3. Inspection & Verification Workflow
- **Manifest Verification**: Upload delivery manifests to systematically verify incoming stock against expectations.
- **Batch Processing**: Type in a product code and quantity, and hit "Confirm Batch" to instantly verify received line-items.
- **Error Checking**: Filter views to quickly spot "Code Not Found" or "No Image" errors in the manifest.
- **Safe Saves**: "Save Overwrite" and "Save As..." functions ensure your verification progress is always securely logged.

### 4. Stock Management 
- **Stock Tracking**: Dedicated workspace to load, filter, and inspect internal stock files (`stock_data.csv`).
- **Unified Search**: Uses the same powerful global and code-segmented search tools to hunt down inventory in stock.

### 5. Web Scraping & Data Collection
- **Internal Scripts**: Integrated Python scrapers to collect missing catalog data, download product images, and assemble product portfolios automatically from supplier websites.

## 🛠️ Technology Stack
- **GUI Framework**: PyQt6
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: PyTorch, Sentence-Transformers, Llama.cpp (via `llama_cpp_python`)
- **Database**: SQLite3

## 📦 Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   pip install -r mapper/requirements_mapper.txt
   ```
2. Run the main application:
   ```bash
   python main.py
   ```
