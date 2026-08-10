import json

with open(r'C:\Users\Anas Mohamed\PyCharmMiscProject\offer_webapp\src\data\A2_parsed_sets.json', encoding='utf-8') as f:
    sets = json.load(f)

md = "\n### Extracted Sets from A2.xls\n\n"
md += "| Set Name | Item Count |\n|---|---|\n"
for s in sets:
    md += f"| {s['set_name']} | {len(s['items'])} |\n"
    
with open('a2_md_snippet.txt', 'w', encoding='utf-8') as f:
    f.write(md)
