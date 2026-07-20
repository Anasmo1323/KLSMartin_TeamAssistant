import pandas as pd

def merge_translations():
    file2_path = r"C:\Users\Anas Mohamed\PyCharmMiscProject\ui\KLS_All_Products.xlsx"
    file1_path = r"C:\Users\Anas Mohamed\PyCharmMiscProject\ui\KLS_All_Products traslated .xlsx"
    output_path = r"C:\Users\Anas Mohamed\PyCharmMiscProject\ui\KLS_All_Products traslated_merged.xlsx"

    print("Loading files...")
    # Load both Excel files
    df1 = pd.read_excel(file1_path)
    df2 = pd.read_excel(file2_path)

    # Ensure 'code' columns are treated as strings for reliable matching
    df1['code_norm'] = df1['code'].astype(str).str.strip().str.lower()
    df2['code_norm'] = df2['code'].astype(str).str.strip().str.lower()

    # Drop empty codes or empty translations from file 1 to build a clean mapping dictionary
    valid_df1 = df1.dropna(subset=['code', 'description_arabic'])
    
    # Create a dictionary of {code_norm: description_arabic}
    translation_map = dict(zip(valid_df1['code_norm'], valid_df1['description_arabic']))
    print(f"Loaded {len(translation_map)} valid translations from the source file.")

    # Function to update the translation in df2
    def update_arabic(row):
        code = row['code_norm']
        if code in translation_map:
            # Overwrite with the translation from file 1
            return translation_map[code]
        # Otherwise, leave it as it was in file 2
        return row['arabic description']

    print("Merging translations...")
    df2['arabic description'] = df2.apply(update_arabic, axis=1)

    # Clean up the temporary 'code_norm' column before saving
    df2 = df2.drop(columns=['code_norm'])

    print(f"Saving updated file to: {output_path}")
    df2.to_excel(output_path, index=False)
    print("Merge complete!")

if __name__ == "__main__":
    merge_translations()
