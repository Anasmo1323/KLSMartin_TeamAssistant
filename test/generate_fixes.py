import re
import os

fixes = []
with open('all_unique_items.txt', 'r', encoding='utf-8') as f:
    items = [line.strip() for line in f if line.strip()]

def clean_item(item):
    orig = item
    
    # Common medical term misspellings
    item = re.sub(r'(?i)\babdomenal\b', 'Abdominal', item)
    item = re.sub(r'(?i)\badison\b', 'Adson', item)
    item = re.sub(r'(?i)\baligator\b', 'Alligator', item)
    item = re.sub(r'(?i)\balis\b', 'Allis', item)
    item = re.sub(r'(?i)\banuo\b', 'Ano', item)
    item = re.sub(r'(?i)\bappendex\b', 'Appendix', item)
    item = re.sub(r'(?i)\baortoc\b', 'Aortic', item)
    item = re.sub(r'(?i)\batrery\b', 'Artery', item)
    item = re.sub(r'(?i)\batruamatic\b', 'Atraumatic', item)
    item = re.sub(r'(?i)\bbaipolar\b', 'Bipolar', item)
    item = re.sub(r'(?i)\bbercifascial\b', 'Berci Fascial', item)
    item = re.sub(r'(?i)\bbobcock\b', 'Babcock', item)
    item = re.sub(r'(?i)\bcasber\b', 'Caspar', item)
    item = re.sub(r'(?i)\bcasper\b', 'Caspar', item)
    item = re.sub(r'(?i)\bclowar\b', 'Cloward', item)
    item = re.sub(r'(?i)\bcurrate?\b', 'Curette', item)
    item = re.sub(r'(?i)\bdebakeys\b', 'DeBakey', item)
    item = re.sub(r'(?i)de bakey', 'DeBakey', item)
    item = re.sub(r'(?i)\bdebakey\b', 'DeBakey', item)
    item = re.sub(r'(?i)\bdicector\b', 'Dissector', item)
    item = re.sub(r'(?i)\bdowen\b', 'Down', item)
    item = re.sub(r'(?i)\bforcelim\b', 'Forceps', item)
    item = re.sub(r'(?i)\bforcep\b', 'Forceps', item)
    item = re.sub(r'(?i)\bforceps\b', 'Forceps', item)
    item = re.sub(r'(?i)\bforseps\b', 'Forceps', item)
    item = re.sub(r'(?i)\bforeceps\b', 'Forceps', item)
    item = re.sub(r'(?i)\bgresping\b', 'Grasping', item)
    item = re.sub(r'(?i)\bhand\s*\(4\)', 'Handle No. 4', item)
    item = re.sub(r'(?i)\bhand\s*\(3\)', 'Handle No. 3', item)
    item = re.sub(r'(?i)\bhoklet\b', 'Hooklet', item)
    item = re.sub(r'(?i)\bhummer\b', 'Hammer', item)
    item = re.sub(r'(?i)\binsaflator\b', 'Insufflator', item)
    item = re.sub(r'(?i)\bcaple\b', 'Cable', item)
    item = re.sub(r'(?i)\bkerrision\b', 'Kerrison', item)
    item = re.sub(r'(?i)\bkirrison\b', 'Kerrison', item)
    item = re.sub(r'(?i)\bkerison\b', 'Kerrison', item)
    item = re.sub(r'(?i)\blengenbeck\b', 'Langenbeck', item)
    item = re.sub(r'(?i)\bmacdonal\b', 'MacDonald', item)
    item = re.sub(r'(?i)\bmaliable\b', 'Malleable', item)
    item = re.sub(r'(?i)\bmasbar\b', 'Probe', item)
    item = re.sub(r'(?i)\bmets\b', 'Metz', item)
    item = re.sub(r'(?i)\bmosqute\b', 'Mosquito', item)
    item = re.sub(r'(?i)\bmosqyito\b', 'Mosquito', item)
    item = re.sub(r'(?i)\bmosqutio\b', 'Mosquito', item)
    item = re.sub(r'(?i)\bovam\b', 'Ovum', item)
    item = re.sub(r'(?i)\bpreforator\b', 'Perforator', item)
    item = re.sub(r'(?i)\bpreiosteal\b', 'Periosteal', item)
    item = re.sub(r'(?i)\bresano\b', 'Rozano', item)
    item = re.sub(r'(?i)\bscalple\b', 'Scalpel', item)
    item = re.sub(r'(?i)\bscissior\b', 'Scissors', item)
    item = re.sub(r'(?i)\bscissore\b', 'Scissors', item)
    item = re.sub(r'(?i)\bscissor\b', 'Scissors', item)
    item = re.sub(r'(?i)\bscisssors\b', 'Scissors', item)
    item = re.sub(r'(?i)\bsnager\b', 'Snare', item)
    item = re.sub(r'(?i)\bsnair\b', 'Snare', item)
    item = re.sub(r'(?i)\bspong\b', 'Sponge', item)
    item = re.sub(r'(?i)\bspongeforceps\b', 'Sponge Forceps', item)
    item = re.sub(r'(?i)\bstaightening\b', 'Straightening', item)
    item = re.sub(r'(?i)\bstaight\b', 'Straight', item)
    item = re.sub(r'(?i)\bstaright\b', 'Straight', item)
    item = re.sub(r'(?i)\bstreight\b', 'Straight', item)
    item = re.sub(r'(?i)\bstright\b', 'Straight', item)
    item = re.sub(r'(?i)\bstriaght\b', 'Straight', item)
    item = re.sub(r'(?i)\bstanesky\b', 'Satinsky', item)
    item = re.sub(r'(?i)\bsternnum\b', 'Sternum', item)
    item = re.sub(r'(?i)\bwrigly\b', 'Wrigley', item)
    item = re.sub(r'(?i)\byankar\b', 'Yankauer', item)
    item = re.sub(r'(?i)\byanker\b', 'Yankauer', item)
    item = re.sub(r'(?i)\byankuer\b', 'Yankauer', item)
    item = re.sub(r'(?i)\byunker\b', 'Yankauer', item)
    item = re.sub(r'(?i)\bsuctin\b', 'Suction', item)
    item = re.sub(r'(?i)\bangeled\b', 'Angled', item)
    item = re.sub(r'(?i)\bangel\b', 'Angle', item)
    item = re.sub(r'(?i)\bblant\b', 'Blunt', item)
    item = re.sub(r'(?i)\bruller\b', 'Ruler', item)
    item = re.sub(r'(?i)\brouler\b', 'Ruler', item)
    item = re.sub(r'(?i)\bdoval\b', 'Duval', item)
    item = re.sub(r'(?i)\bflixsable\b', 'Flexible', item)
    item = re.sub(r'(?i)\bextention\b', 'Extension', item)
    item = re.sub(r'(?i)\bretarning\b', 'Retaining', item)
    item = re.sub(r'(?i)\bretaning\b', 'Retaining', item)
    item = re.sub(r'(?i)\btonotomy\b', 'Tenotomy', item)
    item = re.sub(r'(?i)\btrifect\b', 'Trifecta', item)
    item = re.sub(r'(?i)\btympanoplast\b', 'Tympanoplasty', item)
    item = re.sub(r'(?i)\bpreiosteal\b', 'Periosteal', item)
    item = re.sub(r'(?i)\bnippler\b', 'Nibbler', item)
    
    # Custom specific fixes for GS sheet mapping
    if 'Mosquito Forceps ST' in orig or 'Mosquito Forceps  ST' in orig:
        item = 'Mosquito Straight مسكيتو مستقيم'
    if 'Mosquito Forceps Staight' in orig:
        item = 'Mosquito Straight مسكيتو مستقيم'
    if 'Mosquito straight مسكيتو مستقيم' in orig:
        item = 'Mosquito Straight مسكيتو مستقيم'
        
    if 'Towel Clip' in orig or 'Towel Clips' in orig:
        if 'تاول كلبس' in orig:
            item = 'Towel Forceps تاول كلبس'
        else:
            item = 'Towel Forceps'
    if 'Towel Forceps' in orig and 'تاول' in orig:
        item = 'Towel Forceps تاول كلبس'
        
    if 'Mayo Scissor' in orig or 'Mayo Dissecting Scissor' in orig or 'Mayo Dissecting Scissors' in orig:
        if 'مقص' in orig:
            item = 'Mayo Dissecting Scissors مقص'
        else:
            item = 'Mayo Dissecting Scissors'
        
    item = re.sub(r'\s+', ' ', item).strip()
    
    if item != orig:
        fixes.append((orig, item))
    elif item.islower():
        titled = item.title()
        if titled != orig:
            fixes.append((orig, titled))
    return item

for i in items:
    clean_item(i)

out_py = 'SPELLING_FIXES = {\n'
for orig, corrected in fixes:
    orig_esc = orig.replace("\"", "\\\"")
    corr_esc = corrected.replace("\"", "\\\"")
    out_py += f'    "{orig_esc}": "{corr_esc}",\n'
out_py += '}\n\n'
out_py += '''def clean_name(name):
    if not name or str(name).lower() == 'nan':
        return name
        
    name_str = str(name).strip()
    
    # 1. Apply specific spelling dictionary fixes (case-insensitive keys)
    lower_fixes = {k.lower(): v for k, v in SPELLING_FIXES.items()}
    if name_str.lower() in lower_fixes:
        name_str = lower_fixes[name_str.lower()]
    
    # 2. Capitalize first letter of each word (Title Case)
    import re
    def repl(m):
        w = m.group(0)
        return w if w.isupper() else w.capitalize()
    name_str = re.sub(r'[A-Za-z]+', repl, name_str)
    
    # 3. Fix multiple spaces and strip
    name_str = re.sub(r'\s+', ' ', name_str).strip()
    
    return name_str
'''

with open('spelling_fixes.py', 'w', encoding='utf-8') as f:
    f.write(out_py)

with open(r'c:\Users\Anas Mohamed\PyCharmMiscProject\scripts\spelling_fixes.py', 'w', encoding='utf-8') as f:
    f.write(out_py)

print(f"Generated spelling_fixes.py with {len(fixes)} items")
