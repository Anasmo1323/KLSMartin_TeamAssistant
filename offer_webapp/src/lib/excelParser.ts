import * as XLSX from 'xlsx';

export interface ParsedItem {
  option_id?: string;
  code: string;
  base_code: string;
  basic_description: string;
  qty: number;
  image_url: string | null;
  extracted_features: any;
  details: any;
  isStandard: boolean;
}

export interface ParsedGroup {
  group_id: string;
  group_name: string;
  required_qty: number;
  options: ParsedItem[];
}

export interface ParsedSet {
  set_id: string;
  set_name: string;
  groups: ParsedGroup[];
}

export interface ParsedCategory {
  name: string;
  sets: ParsedSet[];
}

export const parseOfferExcel = async (
  file: File, 
  familyCatalog: any
): Promise<ParsedCategory[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const categoriesMap: Record<string, ParsedCategory> = {};
        let idCounter = 1;

        for (const sheetName of workbook.SheetNames) {
          const worksheet = workbook.Sheets[sheetName];
          const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];
          if (!rows || rows.length === 0) continue;
          
          let headerRowIdx = -1;
          // Find header row in this sheet
          for (let i = 0; i < Math.min(20, rows.length); i++) {
            const rowStr = (rows[i] || []).join(' ').toUpperCase();
            if (rowStr.includes('DESCRIPTION') || (rowStr.includes('CODE') && rowStr.includes('QTY'))) {
              headerRowIdx = i;
              break;
            }
          }
          
          if (headerRowIdx === -1) {
            console.warn(`No header row found in sheet ${sheetName}, skipping.`);
            continue;
          }
          
          const headers = rows[headerRowIdx].map(h => String(h || '').toUpperCase().trim());
          const codeIdx = headers.findIndex(h => h.includes('CODE'));
          const descIdx = headers.findIndex(h => h.includes('DESC'));
          const qtyIdx = headers.findIndex(h => h.includes('QTY'));
          
          if (descIdx === -1) {
            console.warn(`No DESCRIPTION column in sheet ${sheetName}, skipping.`);
            continue;
          }
          
          let currentDiscipline = sheetName.trim();
          let currentSet = "General Items";
          let currentGroup = "Options";

          for (let i = headerRowIdx + 1; i < rows.length; i++) {
            const row = rows[i];
            if (!row || row.length === 0) continue;
            
            const code = codeIdx !== -1 ? String(row[codeIdx] || '').trim() : '';
            const desc = String(row[descIdx] || '').trim();
            const qtyRaw = qtyIdx !== -1 ? row[qtyIdx] : '';
            
            // If there is no code and no qty, but there is a description -> Section Header (Subheader)
            if (!code && !qtyRaw && desc) {
              // Peek ahead to next non-empty row to determine if this is a Set or a Group
              let isSet = false;
              for (let j = i + 1; j < rows.length; j++) {
                const nextRow = rows[j];
                if (!nextRow || nextRow.length === 0) continue;
                
                const nextCode = codeIdx !== -1 ? String(nextRow[codeIdx] || '').trim() : '';
                const nextDesc = String(nextRow[descIdx] || '').trim();
                const nextQtyRaw = qtyIdx !== -1 ? nextRow[qtyIdx] : '';
                
                if (!nextDesc && !nextCode) continue; // Skip completely empty rows in lookahead
                
                // If the next valid row also has no code and no qty, then THIS row is a Set.
                if (!nextCode && !nextQtyRaw && nextDesc) {
                  isSet = true;
                }
                break;
              }
              
              if (isSet) {
                currentSet = desc;
              } else {
                currentGroup = desc;
              }
              continue;
            }
            
            if (!desc && !code) continue; // Skip completely empty rows
            
            // Parse quantity
            let qty = parseFloat(String(qtyRaw).replace(/,/g, ''));
            if (isNaN(qty)) qty = 1;
            
            // Lookup family catalog for extra details if available
            let familyDetails: any = null;
            let image_url = null;
            let base_code = code;
            
            if (code) {
              const parts = code.split('-');
              if (parts.length >= 2) {
                base_code = `${parts[0]}-${parts[1]}`;
              }
              
              if (familyCatalog) {
                for (const familyOptions of Object.values(familyCatalog) as any[][]) {
                  const match = familyOptions.find(o => o.code === code);
                  if (match) {
                    familyDetails = match;
                    image_url = match.image_url || match.details?.local_image_path || null;
                    break;
                  }
                }
              }
            }
            
            const parsedItem: ParsedItem = {
              option_id: `opt_${idCounter++}`,
              code: code,
              base_code: familyDetails ? familyDetails.base_code : base_code,
              basic_description: familyDetails ? familyDetails.basic_description : desc,
              qty: qty,
              image_url: image_url,
              extracted_features: familyDetails ? familyDetails.extracted_features : {},
              details: familyDetails ? familyDetails.details : { description: desc },
              isStandard: true
            };
            
            // Build hierarchy
            if (!categoriesMap[currentDiscipline]) {
              categoriesMap[currentDiscipline] = { name: currentDiscipline, sets: [] };
            }
            let setObj = categoriesMap[currentDiscipline].sets.find(s => s.set_name === currentSet);
            if (!setObj) {
              setObj = { set_id: `set_${idCounter++}`, set_name: currentSet, groups: [] };
              categoriesMap[currentDiscipline].sets.push(setObj);
            }
            
            let groupObj = setObj.groups.find(g => g.group_name === currentGroup);
            if (!groupObj) {
              groupObj = { group_id: `grp_${idCounter++}`, group_name: currentGroup, required_qty: 1, options: [] };
              setObj.groups.push(groupObj);
            }
            
            groupObj.options.push(parsedItem);
          }
        }
        
        resolve(Object.values(categoriesMap));
        
      } catch (err) {
        reject(err);
      }
    };
    
    reader.onerror = (error) => {
      reject(error);
    };
    
    reader.readAsArrayBuffer(file);
  });
};
