# KLSMartin Team Assistant (Technowave Inventory Control Terminal)

A comprehensive inventory control, verification, and AI-powered product mapping assistant built with PyQt6. Designed specifically to handle large equipment catalogs, automate data matching, and streamline stock verification.

## 📂 Project Structure
- **`desktop_app/`**: The core Python Desktop Application (PyQt6).
- **`offer_webapp/`**: The Next.js web application.
- **`scripts/`**: Standalone data pipelines, parsing utilities, and scrapers.
- **`data/`**: Core datasets (Excel, JSON) shared across the applications.

## 🚀 Key Features

### 1. KLS Master Catalog 
- **Dynamic Product Browsing**: Fast, responsive data tables to navigate massive product lists seamlessly.
- **Responsive Design**: Fluid UI layout without hardcoded constraints, allowing dynamic window resizing in all directions.
- **Advanced Filtering (Accordion UI)**: Filter products efficiently using a custom-built, auto-expanding Accordion Sidebar containing inline search bars for:
  - *Categories*
  - *Brochures*: Intelligently grouped into a collapsible tree structure, mapped logically with dynamic bundling.
  - *Instrument Sets*: Parses `ALMA_Sets_Export.xlsx` to instantly filter the master table down to the exact SKUs making up a specific instrument set.
- **State Toggling**: A unified dropdown to instantly filter the global catalog by Product State (All / Active / Inactive), with dynamic color-coding in the data grid.
- **Crash-Proof Debouncing**: All search inputs and checkbox filters are heavily debounced (300ms) to ensure smooth performance even when rapidly interacting with massive datasets.
- **Search Capabilities**:
  - *Global Search*: Full-text search across all descriptions and data fields.
  - *Smart Segmented Search*: A dynamic composite text field that automatically parses both standard `XX-XXX-XX-XX` codes and shorter dot-separated codes (like `XX.XXX.XX`) natively from copy-pasting.
- **Offers Manager**: Quickly build, review, and manage lists of items as an "Offer". Export directly to dynamically generated PowerPoint presentations, with one-click automatic PDF compilation via Microsoft COM integration.
  - *Set Loading*: Features a dedicated dialog to search and instantly inject all constituent SKUs of a specific Instrument Set directly into the Offer List with correct quantities.
  - *Rapid Entry*: Keyboard shortcuts ('Enter' key) inside the Master Grid seamlessly trigger the quantity entry prompt.
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
- **Non-Destructive Saves**: Replaces standard overwrites with surgical `openpyxl` modifications. When saving, the app opens the original Excel file natively, paints un-cleared codes yellow, calculates missing quantities on the far right, and saves it seamlessly without stripping existing graphs, macros, or formatting.

### 4. Stock Management 
- **Stock Tracking**: Dedicated workspace to load, filter, and inspect internal stock files (`stock_data.csv`).
- **Unified Search**: Uses the same powerful global and code-segmented search tools to hunt down inventory in stock.

### 5. Web Scraping & Data Collection
- **Internal Scripts**: Integrated Python scrapers (`alma_scrap.py`) to collect missing catalog data, download product images, and assemble product portfolios automatically from authenticated portals (e.g. ALMA).
- **Resilient Image Scraping**: Features intelligent resumable extraction logic, dynamically bypassing already downloaded images to gracefully handle timeouts and network disconnects.

## 🛠️ Technology Stack
- **GUI Framework**: PyQt6
- **Data Processing**: Pandas, NumPy, OpenPyXL
- **Machine Learning**: PyTorch, Sentence-Transformers, Llama.cpp (via `llama_cpp_python`)
- **Database**: SQLite3

## 📦 Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   pip install -r mapper/requirements_mapper.txt
   ```
2. Run the main application:
   ```bash
   cd desktop_app
   python main.py
   ```
