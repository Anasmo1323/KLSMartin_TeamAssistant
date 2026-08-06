
import pandas as pd
df = pd.read_excel('MCC_OfferList_Deduplicated.xlsx', sheet_name='ENT')
in_set = False
for index, row in df.iterrows():
    desc = str(row.get('DESCRIPTION', ''))
    if 'Tonsillectomy Set (4)' in desc:
        in_set = True
    if in_set:
        print(row.get('#'), '|', row.get('CODE'), '|', desc)
    if in_set and 'Needle Holder' in desc:
        break

