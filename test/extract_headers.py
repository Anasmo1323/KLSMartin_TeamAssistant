import pandas as pd

df = pd.read_excel('MCC_OfferList.one copy.xlsx', sheet_name='GS')
out = []
for index, row in df.iterrows():
    if pd.isna(row.get('#')) and not pd.isna(row.get('DESCRIPTION')):
        desc = str(row['DESCRIPTION']).strip()
        qty = str(row.get('QTY', ''))
        out.append(f"{index}: {desc} | QTY: {qty}")

with open('mcc_gs_headers.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
