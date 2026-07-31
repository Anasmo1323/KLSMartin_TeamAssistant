import pandas as pd

def parse_generic(description: str) -> dict:
    if pd.isna(description) or not isinstance(description, str):
        return {"family": None, "modifiers": None}
    desc = description.strip()
    parts = [p.strip() for p in desc.split(",")]
    return {
        "family": parts[0] if parts else desc,
        "modifiers": ", ".join(parts[1:]).strip() if len(parts) > 1 else None
    }

df = pd.read_excel(r"C:\Users\Anas Mohamed\PyCharmMiscProject\KLS_All_Products.xlsx")
active = df[df["state"] == "Active"].copy()

# Filter for implants (prefixes 25, 26, 50, 51, 52)
active["prefix"] = active["code"].astype(str).str[:2]
implants = active[active["prefix"].isin(["25", "26", "50", "51", "52"])]

print(f"Total active implants: {len(implants)}")

# Parse and count families
results = implants["description"].apply(parse_generic).apply(pd.Series)
implants["extracted_family"] = results["family"].str.title()
implants["extracted_modifiers"] = results["modifiers"]

family_counts = implants["extracted_family"].value_counts()

print("\n=== Top 20 Extracted Families for Implants ===")
print(family_counts.head(20).to_string())

print("\n=== Sample of low-frequency/messy families (potential issues) ===")
print(family_counts[family_counts == 1].head(15).to_string())

print("\n=== Sample of modifiers extracted ===")
sample = implants[["description", "extracted_family", "extracted_modifiers"]].sample(15, random_state=42)
for _, row in sample.iterrows():
    print(f"\nRaw: {row['description']}")
    print(f"  -> Fam: {row['extracted_family']}")
    print(f"  -> Mod: {row['extracted_modifiers']}")
