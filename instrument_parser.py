# instrument_parser.py
"""
Two-track pipeline for parsing KLS Martin product descriptions into
structured family/variation data.

Track A -- Deterministic regex parser for well-formed descriptions (~83%)
Track B -- Grammar-constrained LLM extraction for ALL-CAPS shorthand (~17%)

Phase 0 -- Split active/inactive items into separate files
Phase 1 -- Classify each item's schema and extract structured fields
Phase 2 -- Standardise all extracted columns
Phase 3 -- Output as JSON (hierarchical family -> variations)
"""

import json
import os
import re
import textwrap

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_PATH = r"C:\Users\Anas Mohamed\PyCharmMiscProject\models\qwen2.5-14b-instruct-q4_k_m.gguf"
CTX_SIZE = 2048
N_THREADS = 6

EXCEL_PATH = r"C:\Users\Anas Mohamed\PyCharmMiscProject\KLS_All_Products.xlsx"
OUTPUT_DIR = r"C:\Users\Anas Mohamed\PyCharmMiscProject"


# ===========================================================================
# Phase 0 -- Split Active / Inactive
# ===========================================================================

def split_active_inactive(excel_path: str = EXCEL_PATH, output_dir: str = OUTPUT_DIR):
    """
    Read the master Excel file, move inactive items to a separate file,
    and return only the active DataFrame.
    """
    print(f"Loading master file: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"  Total items: {len(df)}")

    active = df[df["state"] == "Active"].copy().reset_index(drop=True)
    inactive = df[df["state"] != "Active"].copy().reset_index(drop=True)

    print(f"  Active:   {len(active)}")
    print(f"  Inactive: {len(inactive)}")

    # Save inactive to a separate file
    inactive_path = os.path.join(output_dir, "KLS_Inactive_Products.xlsx")
    inactive.to_excel(inactive_path, index=False)
    print(f"  Inactive items saved to: {inactive_path}")

    # Overwrite master with active-only
    active.to_excel(excel_path, index=False)
    print(f"  Master file updated with active items only.")

    return active


# ===========================================================================
# Schema Classification
# ===========================================================================

# Maps the 2-digit code prefix to a schema type
_PREFIX_SCHEMA = {
    # Instruments (surgical tools)
    "09": "instrument", "10": "instrument", "11": "instrument",
    "12": "instrument", "13": "instrument", "14": "instrument",
    "15": "instrument", "16": "instrument", "18": "instrument",
    "20": "instrument", "21": "instrument", "22": "instrument",
    "23": "instrument", "24": "instrument", "28": "instrument",
    "30": "instrument", "31": "instrument", "32": "instrument",
    "33": "instrument", "35": "instrument", "36": "instrument",
    "37": "instrument", "38": "instrument", "39": "instrument",
    "40": "instrument", "41": "instrument", "42": "instrument",
    "43": "instrument", "44": "instrument", "46": "instrument",
    "47": "instrument", "48": "instrument", "73": "instrument",
    # Implants / plates / screws / biomaterials
    "01": "implant", "25": "implant", "26": "implant",
    "50": "implant", "51": "implant", "52": "implant",
    "53": "implant", "54": "implant",
    # Devices / units / systems
    "17": "device", "80": "device", "83": "device",
    "84": "device", "85": "device", "89": "device",
    # Accessories / containers / trays / storage
    "04": "accessory", "08": "accessory", "19": "accessory",
    "27": "accessory", "55": "accessory", "56": "accessory",
    "59": "accessory", "76": "accessory", "77": "accessory",
    "78": "accessory", "79": "accessory",
    "90": "accessory", "92": "accessory", "99": "accessory",
}

# Spare part detection: code suffix -98 or keywords
_SPARE_KEYWORDS = re.compile(
    r"\b(spare|ersatz|substitute|allein|only\s+for|replacement\s+for|"
    r"screw\s+only|spring\s+only|mandrin\s+fuer|pos\.\s*\d+)\b",
    re.IGNORECASE,
)


def classify_schema(code: str, description: str) -> str:
    """
    Determine the schema type for an item based on its code prefix,
    code suffix, and description keywords.

    Returns one of: 'instrument', 'implant', 'device', 'accessory', 'spare_part'
    """
    if pd.isna(code) or pd.isna(description):
        return "unknown"

    code_str = str(code).strip()

    # Spare parts override: suffix -98 or spare-part keywords
    if code_str.endswith("-98") or _SPARE_KEYWORDS.search(str(description)):
        return "spare_part"

    # Label clips (suffix -99) are accessories
    if code_str.endswith("-99"):
        return "accessory"

    prefix = code_str[:2]
    return _PREFIX_SCHEMA.get(prefix, "unknown")


# ===========================================================================
# Track A -- Deterministic Regex Parser
# ===========================================================================

# Inventor attribution
_INVENTOR_RE = re.compile(
    r",?\s*(?:acc(?:ording)?\.?\s*(?:to)?|nach)\s+(.+?)(?=,|$)",
    re.IGNORECASE,
)

# Shape keywords
_SHAPE_RE = re.compile(
    r"\b(straight|str\.?|curved|cvd\.?|angled|ang\.?|bayonet|bay\.?)\b",
    re.IGNORECASE,
)
_SHAPE_MAP = {
    "straight": "Straight", "str": "Straight", "str.": "Straight",
    "curved": "Curved", "cvd": "Curved", "cvd.": "Curved",
    "angled": "Angled", "ang": "Angled", "ang.": "Angled",
    "bayonet": "Angled", "bay": "Angled", "bay.": "Angled",
}

# Length
_LENGTH_RE = re.compile(
    r"(?:(?:total\s+)?length\s+)?(\d+[.,]?\d*)\s*(cm|mm)\b",
    re.IGNORECASE,
)

# Tip types
_TIP_RE = re.compile(
    r"\b((?:blunt|sharp|bl|sh)(?:\s*/\s*(?:blunt|sharp|bl|sh))?)\b"
    r"|\b(\d+\s*x\s*\d+\s*teeth)\b",
    re.IGNORECASE,
)
_TIP_NORMALISE = {
    "bl": "blunt", "sh": "sharp",
    "bl/bl": "blunt/blunt", "bl/sh": "blunt/sharp",
    "sh/bl": "sharp/blunt", "sh/sh": "sharp/sharp",
}

# Dimensions
_DIMENSIONS_RE = re.compile(
    r"(\d+[.,]?\d*)\s*(?:x|\*|X)\s*(\d+[.,]?\d*)\s*(cm|mm)\b",
    re.IGNORECASE,
)

# Modifier keywords (should NOT be in family name)
_MODIFIER_KEYWORDS = re.compile(
    r"\b("
    r"straight|str\.?|curved|cvd\.?|angled|ang\.?|bayonet|bay\.?"
    r"|blunt|bl\.?|sharp|sh\.?"
    r"|right|left|long|short|slim|slender|solid|hollow|round|mini"
    r"|with|w/|w/o|without|ratchet|lock|fenestrated|serrated|smooth"
    r"|titanium|ti\b|tc\b|diamond|gold|atrauma|supercut"
    r"|sterile|ster\.?|demo|detachable"
    r"|safety[- ]wave"
    r"|length|total\s+length|cutting\s+length"
    r"|handle\s+diameter"
    r"|thread\s+size"
    r"|figure|fig\.?|no\.?|nr\.?"
    r"|pack\s+of|pcs\.?"
    r")\b",
    re.IGNORECASE,
)


def _is_shorthand(desc: str) -> bool:
    """Detect ALL-CAPS shorthand descriptions that need LLM parsing."""
    if not desc or pd.isna(desc):
        return False
    alpha_chars = [c for c in desc if c.isalpha()]
    if not alpha_chars:
        return False
    upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    return upper_ratio > 0.8


def parse_instrument_regex(description: str) -> dict:
    """
    Parse a well-formed instrument description using regex.
    Returns dict with: family, inventor, shape, length, tip_type, modifiers
    """
    result = {
        "family": None, "inventor": None, "shape": None,
        "length": None, "dimensions": None, "tip_type": None, "modifiers": None,
    }

    if pd.isna(description) or not isinstance(description, str):
        return result

    desc = description.strip()
    parts = [p.strip() for p in desc.split(",")]

    # --- Inventor ---
    inv_match = _INVENTOR_RE.search(desc)
    if inv_match:
        result["inventor"] = inv_match.group(1).strip()

    # --- Shape ---
    shape_match = _SHAPE_RE.search(desc)
    if shape_match:
        raw = shape_match.group(1).lower().rstrip(".")
        result["shape"] = _SHAPE_MAP.get(raw, raw.title())

    # --- Length ---
    length_match = _LENGTH_RE.search(desc)
    if length_match:
        num = length_match.group(1).replace(",", ".")
        unit = length_match.group(2).lower()
        result["length"] = f"{num} {unit}"

    # --- Dimensions ---
    dimensions_match = _DIMENSIONS_RE.search(desc)
    if dimensions_match:
        num1 = dimensions_match.group(1).replace(",", ".")
        num2 = dimensions_match.group(2).replace(",", ".")
        unit = dimensions_match.group(3).lower()
        result["dimensions"] = f"{num1}x{num2} {unit}"

    # --- Tip type ---
    tip_match = _TIP_RE.search(desc)
    if tip_match:
        raw_tip = (tip_match.group(1) or tip_match.group(2)).strip().lower()
        result["tip_type"] = _TIP_NORMALISE.get(raw_tip, raw_tip)

    # --- Family name ---
    family_parts = []
    modifier_parts = []
    hit_modifier = False

    for part in parts:
        clean = _INVENTOR_RE.sub("", part).strip()
        if not clean:
            continue

        is_mod = (
            _SHAPE_RE.search(clean)
            or _LENGTH_RE.search(clean)
            or _TIP_RE.search(clean)
            or _MODIFIER_KEYWORDS.search(clean)
            or re.match(r"^\d+[.,]?\d*\s*(cm|mm)$", clean, re.IGNORECASE)
        )

        if is_mod and not hit_modifier:
            hit_modifier = True

        if hit_modifier:
            if not re.fullmatch(r"\d+[.,]?\d*\s*(cm|mm)", clean, re.IGNORECASE):
                modifier_parts.append(clean)
        else:
            family_parts.append(clean)

    if not family_parts and parts:
        family_parts.append(parts[0].strip())

    result["family"] = ", ".join(family_parts).strip().rstrip(",")

    # Leftover modifiers
    if modifier_parts:
        filtered = []
        for m in modifier_parts:
            m_lower = m.lower().strip()
            if result["shape"] and m_lower == result["shape"].lower():
                continue
            if result["length"] and m_lower == result["length"]:
                continue
            if result["tip_type"] and m_lower == result["tip_type"]:
                continue
            filtered.append(m)
        if filtered:
            result["modifiers"] = ", ".join(filtered)

    return result


def parse_generic(description: str) -> dict:
    """
    Minimal parser for non-instrument items (implants, devices, accessories,
    spare parts). Extracts family by taking the first comma-separated chunk.
    """
    result = {
        "family": None, "inventor": None, "shape": None,
        "length": None, "tip_type": None, "modifiers": None,
    }

    if pd.isna(description) or not isinstance(description, str):
        return result

    desc = description.strip()
    parts = [p.strip() for p in desc.split(",")]

    # Family = first chunk (the product name)
    result["family"] = parts[0] if parts else desc

    # Remaining chunks = modifiers
    if len(parts) > 1:
        result["modifiers"] = ", ".join(parts[1:]).strip()

    # Try to extract inventor even from non-instruments
    inv_match = _INVENTOR_RE.search(desc)
    if inv_match:
        result["inventor"] = inv_match.group(1).strip()
        # Remove inventor from family
        result["family"] = _INVENTOR_RE.sub("", result["family"]).strip().rstrip(",")

    return result


# ===========================================================================
# Track B -- LLM Extraction (shorthand descriptions)
# ===========================================================================

GBNF_DICT_GRAMMAR = r'''
root   ::= "{" ws (pair ("," ws pair)*)? ws "}"
pair   ::= string ws ":" ws string
string ::= "\"" chars "\""
chars  ::= char*
char   ::= [^"\\] | "\\" escape
escape ::= ["\\/bfnrt]
ws     ::= [ \t\n]*
'''

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a medical instrument deduplication assistant.
    You will receive a list of unique family names extracted from a catalogue.
    Many of these families are semantic duplicates of each other due to typos, 
    abbreviations, or alternate word orders (e.g., 'Forcep' vs 'Forceps', 
    'Microneedle Holder' vs 'Micro Needle Holder').

    Identify only the families that are duplicates of another family in the list.
    Return a JSON dictionary mapping the duplicate name to its canonical name.
    Do NOT include families that do not have a duplicate.
    Return ONLY valid JSON.
""")


def _build_llm():
    """Load the GGUF model once and return the Llama instance + grammar."""
    from llama_cpp import Llama, LlamaGrammar

    grammar = LlamaGrammar.from_string(GBNF_DICT_GRAMMAR)
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,
        n_threads=N_THREADS,
        verbose=False,
    )
    return llm, grammar


def consolidate_families(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> pd.DataFrame:
    """Use the LLM to find semantic duplicates among unique family names and merge them."""
    unique_families = sorted([f for f in df["family"].dropna().unique() if str(f).strip()])
    
    if not unique_families:
        return df

    llm, grammar = _build_llm()
    
    cache_path = os.path.join(output_dir, "llm_family_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass

    batch_size = 100
    batches = [unique_families[i:i + batch_size] for i in range(0, len(unique_families), batch_size)]
    
    print(f"\n[!] LLM Family Consolidation: {len(unique_families)} families in {len(batches)} batches.")
    
    global_mapping = {}
    
    from tqdm import tqdm
    for idx, batch in enumerate(tqdm(batches, desc="LLM Consolidating", unit="batch"), start=1):
        batch_key = "|".join(batch)
        if batch_key in cache:
            global_mapping.update(cache[batch_key])
            continue
            
        prompt = "Families:\n" + "\n".join(batch)
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            grammar=grammar,
            max_tokens=1024,
            temperature=0.0,
            top_p=1.0,
        )
        
        raw_json = response["choices"][0]["message"]["content"]
        try:
            mapping = json.loads(raw_json)
        except json.JSONDecodeError:
            tqdm.write(f"    [!] JSON decode failed on batch {idx}: {raw_json}")
            mapping = {}
            
        cache[batch_key] = mapping
        global_mapping.update(mapping)
        
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
            
    if global_mapping:
        print(f"  [+] Applying {len(global_mapping)} semantic merges...")
        df["family"] = df["family"].replace(global_mapping)
        
    return df


# ===========================================================================
# Phase 1 -- Unified Extraction
# ===========================================================================

PARSED_COLUMNS = ["family", "inventor", "shape", "length", "tip_type", "modifiers"]


def extract_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each row, classify its schema and route to the appropriate parser.
    Adds columns: schema, family, inventor, shape, length, tip_type, modifiers.
    The original 'description' column is preserved unchanged.
    """
    df = df.copy()

    # Step 1: classify schema
    df["schema"] = df.apply(
        lambda row: classify_schema(row["code"], row["description"]), axis=1
    )
    print(f"\n  Schema distribution:")
    for schema, count in df["schema"].value_counts().items():
        print(f"    {schema:<15} {count:>5}")

    # Step 2: initialise parsed columns
    for col in PARSED_COLUMNS:
        df[col] = None

    # Step 3: route by schema
    instrument_mask = df["schema"] == "instrument"
    non_instrument_mask = ~instrument_mask

    # Parse non-instruments with generic parser (fast)
    print(f"\n  Parsing {non_instrument_mask.sum()} non-instrument items (generic parser)...")
    for idx in df[non_instrument_mask].index:
        parsed = parse_generic(df.at[idx, "description"])
        for col in PARSED_COLUMNS:
            df.at[idx, col] = parsed[col]

    # Parse instruments
    instrument_df = df[instrument_mask]
    print(f"  Parsing {len(instrument_df)} instrument items...")

    for idx in instrument_df.index:
        desc = df.at[idx, "description"]
        parsed = parse_instrument_regex(desc)
        for col in PARSED_COLUMNS:
            df.at[idx, col] = parsed[col]

    print(f"    Regex (Track A): {len(instrument_df)}")

    return df


# ===========================================================================
# Phase 2 -- Data Standardisation
# ===========================================================================

def standardise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalise extracted columns:
      - family   : strip whitespace, title-case
      - inventor : strip whitespace, title-case
      - length   : commas -> decimals, lowercase
      - Convert string 'None' / 'none' / '' -> pd.NA
    """
    df = df.copy()

    # --- family ---
    # Normalise compound medical prefixes (e.g. "Micro Needle" -> "Microneedle")
    df["family"] = (
        df["family"].astype(str)
        .str.replace(r'\b(micro|neuro|osteo|hemo|cardio|electro)\s+', r'\1', regex=True, flags=re.IGNORECASE)
        .str.replace(r'[\s\-]+', ' ', regex=True)
        .str.strip().str.title()
    )

    # --- inventor ---
    df["inventor"] = df["inventor"].astype(str).str.strip().str.title()

    # --- length ---
    df["length"] = (
        df["length"].astype(str)
        .str.replace(",", ".", regex=False)
        .str.strip().str.lower()
    )

    # --- tip_type ---
    df["tip_type"] = df["tip_type"].astype(str).str.strip().str.lower()

    # --- modifiers ---
    df["modifiers"] = df["modifiers"].astype(str).str.strip()

    # --- Null coercion ---
    none_variants = {"None", "none", "NONE", "null", "Null", "NULL", "", "nan", "NaN"}
    for col in PARSED_COLUMNS:
        df[col] = df[col].where(~df[col].isin(none_variants), other=pd.NA)

    return df


# ===========================================================================
# Phase 3 -- JSON Output
# ===========================================================================

def build_json(df: pd.DataFrame) -> dict:
    """
    Build a hierarchical JSON structure grouped by family.

    Structure:
    {
        "Scalpel Handle": {
            "schema": "instrument",
            "items": [
                {
                    "code": "10-100-04-07",
                    "description": "Scalpel handle, no. 4, length 13.5 cm",
                    "inventor": null,
                    "shape": null,
                    "length": "13.5 cm",
                    "tip_type": null,
                    "modifiers": "no. 4"
                },
                ...
            ]
        },
        ...
    }
    """
    output = {}

    # Fill NA for grouping
    df_work = df.copy()
    df_work["family"] = df_work["family"].fillna("(Unclassified)")

    grouped = df_work.groupby("family")

    for family, group_df in sorted(grouped, key=lambda g: g[0]):
        # Use the most common schema for this family
        schema = group_df["schema"].mode().iloc[0] if len(group_df["schema"].mode()) > 0 else "unknown"

        items = []
        for _, row in group_df.iterrows():
            item = {
                "code": row.get("code"),
                "description": row.get("description"),
                "inventor": row["inventor"] if pd.notna(row.get("inventor")) else None,
                "shape": row["shape"] if pd.notna(row.get("shape")) else None,
                "length": row["length"] if pd.notna(row.get("length")) else None,
                "tip_type": row["tip_type"] if pd.notna(row.get("tip_type")) else None,
                "modifiers": row["modifiers"] if pd.notna(row.get("modifiers")) else None,
                "brochures": row.get("brochures") if pd.notna(row.get("brochures")) else None,
                "state": row.get("state") if pd.notna(row.get("state")) else None,
            }
            items.append(item)

        output[family] = {
            "schema": schema,
            "count": len(items),
            "items": items,
        }

    return output


# ===========================================================================
# Pipeline Runners
# ===========================================================================

def run_from_excel(
    excel_path: str = EXCEL_PATH,
    output_dir: str = OUTPUT_DIR,
    split_inactive: bool = True,
    use_llm: bool = True,
):
    """
    Full pipeline: split active/inactive -> extract -> standardise -> JSON.
    """
    if split_inactive:
        print("=" * 60)
        print("Phase 0 -- Splitting active / inactive items")
        print("=" * 60)
        active_df = split_active_inactive(excel_path, output_dir)
    else:
        active_df = pd.read_excel(excel_path)
        active_df = active_df[active_df["state"] == "Active"].copy().reset_index(drop=True)
        print(f"Loaded {len(active_df)} active items (no split).")

    print(f"\n{'=' * 60}")
    print(f"Phase 1 -- Extraction ({len(active_df)} items)")
    print("=" * 60)
    df_parsed = extract_all(active_df)

    print(f"\n{'=' * 60}")
    print("Phase 2 -- Standardisation")
    print("=" * 60)
    df_clean = standardise(df_parsed)
    
    if use_llm:
        print(f"\n{'=' * 60}")
        print("Phase 2.5 -- LLM Consolidation")
        print("=" * 60)
        df_clean = consolidate_families(df_clean, output_dir=output_dir)

    print(f"\n{'=' * 60}")
    print("Phase 3 -- JSON Output")
    print("=" * 60)
    catalogue = build_json(df_clean)

    json_path = os.path.join(output_dir, "KLS_Product_Families.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(catalogue, f, indent=2, ensure_ascii=False)

    n_families = len(catalogue)
    n_items = sum(v["count"] for v in catalogue.values())
    print(f"\n  Families: {n_families}")
    print(f"  Items:    {n_items}")
    print(f"  Saved to: {json_path}")

    return df_clean, catalogue


# ===========================================================================
# Demo with sample data
# ===========================================================================

SAMPLE_DATA = [
    # Instruments -- well-formed
    ("11-002-14-07", "Scissors, according to Mayo, SuperCut, straight, serrated, total length 14 cm", "Active"),
    ("11-100-11-07", "Operating scissors, blunt/blunt, straight, length 12 cm", "Active"),
    ("20-002-15-07", "Microneedle holder, straight, with ratchet lock, safety-wave, diamond-coated, length 15 cm", "Active"),
    ("12-100-18-07", "Dressing forceps, standard pattern, length 18 cm", "Active"),
    ("10-148-03-07", "Scalpel handle, acc. to Kaye, solid, scalpel handle no. 3, length 15 cm", "Active"),
    # Instruments -- shorthand
    ("11-200-14-07", "METZENB. SCS, CVD., BL/BL, 14,5 CM", "Active"),
    ("11-300-17-07", "MAYO SCS, STR., 17 CM", "Active"),
    ("20-001-01-07", "MICRO NEEDLEHOLDER, CVD., W. LOCK, 15 CM", "Active"),
    # Implants
    ("25-002-02-09", "LevelOne Fixation, micro mesh, 1.0 mm, plate profile 0.6 mm, 2-hole", "Active"),
    ("26-012-05-09", "smartDrive STANDARD SCREW 1.2x5 MM", "Active"),
    # Devices
    ("80-010-02-04", "ME 102", "Active"),
    ("89-700-00-04", "marLED E3 stand, mobile", "Active"),
    # Accessories
    ("56-170-16-01", "ROUND BOWL, H = 74, 150 MM, 0.75 L", "Active"),
    # Spare parts
    ("11-100-90-98", "SCREW ONLY FOR 11-100-11", "Active"),
    ("20-678-90-98", "SCHRAUBE FUER FEDER ALLEIN", "Active"),
    # Inactive (should be filtered out)
    ("00-000-00-25", "Test item inactive", "Inactive"),
]


def main():
    """Demo run using sample data."""
    # Build a sample DataFrame
    df = pd.DataFrame(SAMPLE_DATA, columns=["code", "description", "state"])

    print("=" * 60)
    print("Phase 0 -- Filter active items")
    print("=" * 60)
    active = df[df["state"] == "Active"].copy().reset_index(drop=True)
    inactive = df[df["state"] != "Active"].copy().reset_index(drop=True)
    print(f"  Active: {len(active)},  Inactive: {len(inactive)}")

    # Check model availability
    llm_available = (
        os.path.isfile(MODEL_PATH)
        and os.path.getsize(MODEL_PATH) > 1_000_000_000
    )
    if not llm_available:
        print(f"\n  [!] Model not found or incomplete at {MODEL_PATH}")
        print("      Shorthand rows will use regex fallback.\n")

    print(f"\n{'=' * 60}")
    print(f"Phase 1 -- Extraction ({len(active)} items)")
    print("=" * 60)
    df_parsed = extract_all(active)

    print(f"\n{'=' * 60}")
    print("Phase 2 -- Standardisation")
    print("=" * 60)
    df_clean = standardise(df_parsed)
    
    if llm_available:
        print(f"\n{'=' * 60}")
        print("Phase 2.5 -- LLM Consolidation")
        print("=" * 60)
        df_clean = consolidate_families(df_clean)

    # Print the parsed DataFrame
    display_cols = ["code", "schema", "family", "inventor", "shape", "length", "tip_type", "modifiers"]
    print("\nParsed results:")
    for _, row in df_clean.iterrows():
        print(f"\n  [{row['code']}] {row['description']}")
        print(f"    schema:   {row['schema']}")
        print(f"    family:   {row['family']}")
        print(f"    inventor: {row['inventor']}")
        print(f"    shape:    {row['shape']}")
        print(f"    length:   {row['length']}")
        print(f"    tip_type: {row['tip_type']}")
        print(f"    modifiers:{row['modifiers']}")

    print(f"\n{'=' * 60}")
    print("Phase 3 -- JSON Output")
    print("=" * 60)
    catalogue = build_json(df_clean)
    print(json.dumps(catalogue, indent=2, ensure_ascii=False))

    return df_clean, catalogue


if __name__ == "__main__":
    main()
