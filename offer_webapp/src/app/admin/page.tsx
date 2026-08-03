'use client';

import { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
import styles from './page.module.css';

type CartItem = {
  groupName: string;
  categoryName?: string;
  setName?: string;
  optionDesc: string;
  qty: number;
  code: string;
};

type CustomerInfo = {
  title: string;
  name: string;
  hospital: string;
  phone: string;
  email: string;
  notes: string;
};

type Submission = {
  id: string;
  items: CartItem[];
  timestamp: any;
  status: string;
  customer?: CustomerInfo;
};

export default function AdminPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSub, setSelectedSub] = useState<Submission | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchSubmissions = async () => {
      try {
        const { db } = await import('../../lib/firebase');
        const { collection, getDocs, query, orderBy } = await import('firebase/firestore');
        
        const q = query(collection(db, "submissions"), orderBy("timestamp", "desc"));
        const snapshot = await getDocs(q);
        const subs: Submission[] = [];
        snapshot.forEach((doc) => {
          subs.push({ id: doc.id, ...doc.data() } as Submission);
        });
        setSubmissions(subs);
      } catch (err) {
        console.error("Error fetching submissions:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSubmissions();
  }, []);

  const handleExport = (sub: Submission) => {
    if (sub.items.length === 0) return;
    
    const subTime = sub.timestamp?.toDate ? sub.timestamp.toDate().toLocaleString() : '';
    const submitterName = sub.customer ? `${sub.customer.title || ''} ${sub.customer.name || ''}`.trim() : '';
    const submitterPhone = sub.customer?.phone || '';

    const exportData = sub.items.map(item => ({
      "Code": item.code,
      "Description": item.optionDesc || '',
      "Discpline": item.categoryName || '',
      "Internal Set": item.setName || '',
      "Item Name": item.groupName || '',
      "QTY": item.qty,
      "Submission Time": subTime,
      "Name": submitterName,
      "Phone Number": submitterPhone
    }));

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Selections");
    XLSX.writeFile(wb, `Offer_Export_${sub.id}.xlsx`);
  };

  return (
    <div className={styles.container}>
      <div>
        <p className={styles.subtitle} style={{marginTop: '1rem', fontWeight: 600}}>Admin Dashboard: View live doctor submissions from Firebase.</p>
      </div>

      {loading ? (
        <div style={{color: 'var(--text-secondary)'}}>Loading submissions...</div>
      ) : (
        <div style={{display: 'flex', gap: '2rem'}}>
          {/* Sidebar list */}
          <div style={{width: '300px', display: 'flex', flexDirection: 'column', gap: '1rem'}}>
            <input 
              type="text" 
              placeholder="Search by Submission ID..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-light)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', outline: 'none' }}
            />
            {submissions.filter(s => s.id.toLowerCase().includes(searchQuery.toLowerCase())).length === 0 ? (
               <p style={{color: 'var(--text-muted)'}}>No submissions found.</p>
            ) : (
              submissions.filter(s => s.id.toLowerCase().includes(searchQuery.toLowerCase())).map(sub => (
                <div 
                  key={sub.id} 
                  className={styles.uploadBox} 
                  style={{padding: '1.5rem', borderColor: selectedSub?.id === sub.id ? 'var(--accent-cyan)' : 'var(--border-light)'}}
                  onClick={() => setSelectedSub(sub)}
                >
                  <div style={{fontWeight: 600}}>ID: {sub.id.substring(0,6)}...</div>
                  <div style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
                    Items: {sub.items.length}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Details */}
          <div style={{flex: 1}}>
            {selectedSub ? (
              <>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
                  <h2>Submission: {selectedSub.id}</h2>
                  <button className={styles.exportBtn} style={{marginTop: 0, padding: '0.5rem 1rem'}} onClick={() => handleExport(selectedSub)}>
                    Export Excel
                  </button>
                </div>

                <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '1.25rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.1rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem' }}>Submitter Details</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.95rem' }}>
                    <div><strong style={{color: 'var(--text-secondary)'}}>Name:</strong> {selectedSub.customer ? `${selectedSub.customer.title || ''} ${selectedSub.customer.name}` : 'N/A'}</div>
                    <div><strong style={{color: 'var(--text-secondary)'}}>Hospital:</strong> {selectedSub.customer?.hospital || 'N/A'}</div>
                    <div><strong style={{color: 'var(--text-secondary)'}}>Phone:</strong> {selectedSub.customer?.phone || 'N/A'}</div>
                    <div><strong style={{color: 'var(--text-secondary)'}}>Email:</strong> {selectedSub.customer?.email || 'N/A'}</div>
                    <div><strong style={{color: 'var(--text-secondary)'}}>Date:</strong> {selectedSub.timestamp?.toDate ? selectedSub.timestamp.toDate().toLocaleString() : 'N/A'}</div>
                    {selectedSub.customer?.notes && <div style={{ gridColumn: 'span 2' }}><strong style={{color: 'var(--text-secondary)'}}>Notes:</strong> {selectedSub.customer.notes}</div>}
                  </div>
                </div>
                
                <div className={styles.tableWrapper}>
                  <table>
                    <thead>
                      <tr>
                        <th>Internal Set</th>
                        <th>Item Name</th>
                        <th>Option Code</th>
                        <th>Description</th>
                        <th>Qty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedSub.items.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.setName || '-'}</td>
                          <td>{item.groupName}</td>
                          <td>{item.code}</td>
                          <td>{item.optionDesc}</td>
                          <td>{item.qty}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className={styles.uploadBox} style={{cursor: 'default'}}>
                Select a submission from the left to view details.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
