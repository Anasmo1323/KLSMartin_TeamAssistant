import json

with open('similar_sets.json', 'r') as f:
    pairs = json.load(f)

print("Large Sets with High Overlap (> 60% Jaccard):")
for p in pairs:
    if p['len1'] > 10 and p['len2'] > 10 and p['jaccard'] > 0.6:
        print(f"Set A: '{p['set1']}' ({p['len1']} items)")
        print(f"Set B: '{p['set2']}' ({p['len2']} items)")
        print(f"Overlap: {p['intersect']} items, Jaccard: {p['jaccard']*100:.1f}%\n")
        
print("Subsets (> 80% containment):")
for p in pairs:
    if p['len1'] > 10 and p['len2'] > 10 and p['jaccard'] <= 0.6:
        if p['overlap_1'] > 0.8 or p['overlap_2'] > 0.8:
            print(f"Set A: '{p['set1']}' ({p['len1']} items)")
            print(f"Set B: '{p['set2']}' ({p['len2']} items)")
            print(f"Overlap: {p['intersect']} items (Containment: max({p['overlap_1']*100:.1f}%, {p['overlap_2']*100:.1f}%))\n")
