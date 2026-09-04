import { useState, useEffect } from 'react';
import { db } from '../../lib/firebase';
import { collection, getDocs, addDoc, doc, deleteDoc, serverTimestamp } from 'firebase/firestore';
import { parseOfferExcel } from '../../lib/excelParser';
import styles from './page.module.css';

export default function CustomersTab() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCustomerName, setNewCustomerName] = useState('');
  const [familyCatalog, setFamilyCatalog] = useState<any>(null);

  useEffect(() => {
    fetchCustomers();
    fetchFamilyCatalog();
  }, []);

  const fetchFamilyCatalog = async () => {
    try {
      // In a real deployed app, it's better to host family_catalog.json in public folder
      // or fetch it from Firebase Storage, but here we can try require if it's static
      const data = require('../../data/family_catalog.json');
      setFamilyCatalog(data);
    } catch (e) {
      console.error("Could not load family catalog", e);
    }
  };

  const fetchCustomers = async () => {
    try {
      const snapshot = await getDocs(collection(db, 'customers'));
      const list = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      setCustomers(list);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCustomer = async () => {
    if (!newCustomerName.trim()) return;
    
    let baseSlug = newCustomerName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
    let finalSlug = baseSlug;
    
    // Check if slug already exists to prevent identical links
    let counter = 1;
    while (customers.some(c => c.slug === finalSlug)) {
      finalSlug = `${baseSlug}-${counter}`;
      counter++;
    }
    
    const pin = Math.floor(1000 + Math.random() * 9000).toString(); // random 4-digit
    
    try {
      await addDoc(collection(db, 'customers'), {
        name: newCustomerName.trim(),
        slug: finalSlug,
        pin,
        catalogUrl: null,
        createdAt: serverTimestamp()
      });
      setNewCustomerName('');
      fetchCustomers();
    } catch (e) {
      console.error(e);
      alert("Failed to add customer");
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this customer?")) {
      await deleteDoc(doc(db, 'customers', id));
      fetchCustomers();
    }
  };

  const handleUploadExcel = async (id: string, slug: string, file: File) => {
    try {
      const parsedData = await parseOfferExcel(file, familyCatalog);
      const { updateDoc } = await import('firebase/firestore');
      await updateDoc(doc(db, 'customers', id), { 
        catalogData: parsedData,
        hasCatalog: true
      });
      
      alert("Catalog uploaded successfully!");
      fetchCustomers();
    } catch (e) {
      console.error(e);
      alert("Failed to parse and upload excel file. Check console for details.");
    }
  };

  if (loading) return <p>Loading customers...</p>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <h2>Customer Management</h2>
      <div style={{ display: 'flex', gap: '1rem', maxWidth: '500px' }}>
        <input
          type="text"
          placeholder="New Customer Name (e.g. Cairo University)"
          value={newCustomerName}
          onChange={(e) => setNewCustomerName(e.target.value)}
          style={{ flex: 1, padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-light)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
        />
        <button className={styles.exportBtn} style={{ marginTop: 0 }} onClick={handleAddCustomer}>
          Add Customer
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {customers.length === 0 ? <p style={{color: 'var(--text-secondary)'}}>No customers yet.</p> : null}
        {customers.map(c => (
          <div key={c.id} className={styles.uploadBox} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'default' }}>
            <div>
              <h3>{c.name}</h3>
              <p style={{ margin: '0.25rem 0', color: 'var(--text-secondary)' }}>
                URL: <a href={`/${c.slug}`} target="_blank" rel="noreferrer" style={{color: 'var(--accent-cyan)'}}>{`/${c.slug}`}</a>
              </p>
              <p style={{ margin: 0, color: 'var(--text-secondary)' }}>PIN: <strong style={{color: '#000'}}>{c.pin}</strong></p>
              {c.hasCatalog || c.catalogUrl ? (
                <p style={{ color: '#4caf50', margin: '0.25rem 0', fontWeight: 'bold' }}>✓ Catalog Uploaded</p>
              ) : (
                <p style={{ color: '#ff9800', margin: '0.25rem 0', fontWeight: 'bold' }}>! No Catalog Uploaded</p>
              )}
            </div>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <div>
                <input 
                  type="file" 
                  accept=".xlsx, .xls"
                  id={`file-${c.id}`}
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleUploadExcel(c.id, c.slug, e.target.files[0]);
                    }
                  }}
                />
                <label htmlFor={`file-${c.id}`} className={styles.exportBtn} style={{ cursor: 'pointer', display: 'inline-block', margin: 0 }}>
                  Upload Excel
                </label>
              </div>
              <button 
                className={styles.exportBtn} 
                style={{ backgroundColor: 'var(--accent-red, #ff4444)', margin: 0 }} 
                onClick={() => handleDelete(c.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
