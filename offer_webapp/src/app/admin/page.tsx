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
  const [activeTab, setActiveTab] = useState<'submissions' | 'analytics' | 'emails'>('submissions');
  
  const [selectedSubIds, setSelectedSubIds] = useState<Set<string>>(new Set());
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({});

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [adminCodeInput, setAdminCodeInput] = useState('');

  const ADMIN_CODE = '8899';
  const [notificationEmails, setNotificationEmails] = useState<string[]>([]);
  const [newEmailInput, setNewEmailInput] = useState('');
  const [emailsLoading, setEmailsLoading] = useState(true);


  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchSubmissions = async () => {
      try {
        const { db } = await import('../../lib/firebase');
        const { collection, getDocs, query, orderBy, getDoc, doc } = await import('firebase/firestore');
        
        const q = query(collection(db, "submissions"), orderBy("timestamp", "desc"));
        const snapshot = await getDocs(q);
        const subs: Submission[] = [];
        snapshot.forEach((doc) => {
          subs.push({ id: doc.id, ...doc.data() } as Submission);
        });
        setSubmissions(subs);

        // Fetch emails
        const emailsDoc = await getDoc(doc(db, 'config', 'notifications'));
        if (emailsDoc.exists()) {
          setNotificationEmails(emailsDoc.data().emails || []);
        }
        setEmailsLoading(false);
      } catch (err) {
        console.error("Error fetching submissions:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSubmissions();
  }, [isAuthenticated]);

  const addEmail = async () => {
    if (!newEmailInput || !newEmailInput.includes('@')) return;
    const { doc, setDoc } = await import('firebase/firestore');
    const { db } = await import('../../lib/firebase');
    const updated = [...notificationEmails, newEmailInput];
    await setDoc(doc(db, 'config', 'notifications'), { emails: updated }, { merge: true });
    setNotificationEmails(updated);
    setNewEmailInput('');
  };

  const removeEmail = async (emailToRemove: string) => {
    const { doc, setDoc } = await import('firebase/firestore');
    const { db } = await import('../../lib/firebase');
    const updated = notificationEmails.filter(e => e !== emailToRemove);
    await setDoc(doc(db, 'config', 'notifications'), { emails: updated }, { merge: true });
    setNotificationEmails(updated);
  };

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

  const getSubmissionCategory = (sub: Submission) => {
    if (!sub.items || sub.items.length === 0) return 'Empty';
    const categories = new Set(sub.items.map(i => i.categoryName).filter(Boolean));
    if (categories.size === 1) return Array.from(categories)[0];
    if (categories.size > 1) return 'Mixed';
    return 'Unknown';
  };

  const handleBulkExport = () => {
    const selectedSubs = submissions.filter(s => selectedSubIds.has(s.id));
    if (selectedSubs.length === 0) return;

    let exportData: any[] = [];
    selectedSubs.forEach(sub => {
      const subTime = sub.timestamp?.toDate ? sub.timestamp.toDate().toLocaleString() : '';
      const submitterName = sub.customer ? `${sub.customer.title || ''} ${sub.customer.name || ''}`.trim() : '';
      const submitterPhone = sub.customer?.phone || '';

      const subItems = sub.items.map(item => ({
        "Submission ID": sub.id,
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
      exportData = exportData.concat(subItems);
    });

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Selections");
    XLSX.writeFile(wb, `Offer_Export_Bulk_${selectedSubs.length}_Submissions.xlsx`);
  };

  
  const handleDeleteSubmission = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this submission? This cannot be undone.")) {
      try {
        const { db } = await import('../../lib/firebase');
        const { doc, deleteDoc } = await import('firebase/firestore');
        await deleteDoc(doc(db, "submissions", id));
        setSubmissions(submissions.filter(s => s.id !== id));
        if (selectedSub?.id === id) setSelectedSub(null);
        alert("Submission deleted.");
      } catch (err) {
        console.error("Error deleting submission:", err);
        alert("Failed to delete submission.");
      }
    }
  };

  const handleBulkDelete = async () => {
    if (window.confirm(`Are you sure you want to delete ${selectedSubIds.size} submissions? This cannot be undone.`)) {
      try {
        const { db } = await import('../../lib/firebase');
        const { doc, deleteDoc } = await import('firebase/firestore');
        const idsToDelete = Array.from(selectedSubIds);
        await Promise.all(idsToDelete.map(id => deleteDoc(doc(db, "submissions", id))));
        setSubmissions(submissions.filter(s => !selectedSubIds.has(s.id)));
        setSelectedSubIds(new Set());
        setSelectedSub(null);
        alert("Submissions deleted.");
      } catch (err) {
        console.error("Error bulk deleting:", err);
        alert("Failed to bulk delete.");
      }
    }
  };

  const toggleCategorySelect = (catName: string, subsInCategory: Submission[]) => {
    const allSelected = subsInCategory.length > 0 && subsInCategory.every(s => selectedSubIds.has(s.id));
    const nextSet = new Set(selectedSubIds);
    if (allSelected) {
      subsInCategory.forEach(s => nextSet.delete(s.id));
    } else {
      subsInCategory.forEach(s => nextSet.add(s.id));
    }
    setSelectedSubIds(nextSet);
  };

  if (!isAuthenticated) {
    return (
      <div className={styles.container} style={{ justifyContent: 'center', alignItems: 'center', height: '100vh', display: 'flex' }}>
        <div style={{ background: 'var(--bg-secondary)', padding: '3rem', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-card)' }}>
          <h2 style={{ marginBottom: '1.5rem' }}>Admin Access Required</h2>
          <form onSubmit={(e) => {
            e.preventDefault();
            if (adminCodeInput === ADMIN_CODE) {
              setIsAuthenticated(true);
            } else {
              alert("Incorrect code");
            }
          }}>
            <input 
              type="password"
              placeholder="Enter Admin Code"
              value={adminCodeInput}
              onChange={(e) => setAdminCodeInput(e.target.value)}
              style={{ padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-light)', marginBottom: '1rem', width: '200px', textAlign: 'center', fontSize: '1.2rem', letterSpacing: '0.2rem' }}
            />
            <br />
            <button type="submit" className={styles.exportBtn} style={{ marginTop: '0', width: '200px' }}>
              Login
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div>
        <p className={styles.subtitle} style={{marginTop: '1rem', fontWeight: 600}}>Admin Dashboard: View live doctor submissions from Firebase.</p>
      </div>

            <div style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', borderBottom: '1px solid var(--border-light)' }}>
        <h3 
          style={{ cursor: 'pointer', paddingBottom: '0.5rem', color: activeTab === 'submissions' ? 'var(--accent-cyan)' : 'var(--text-secondary)', borderBottom: activeTab === 'submissions' ? '2px solid var(--accent-cyan)' : 'none' }}
          onClick={() => setActiveTab('submissions')}
        >
          Submissions
        </h3>
        <h3 
          style={{ cursor: 'pointer', paddingBottom: '0.5rem', color: activeTab === 'analytics' ? 'var(--accent-cyan)' : 'var(--text-secondary)', borderBottom: activeTab === 'analytics' ? '2px solid var(--accent-cyan)' : 'none' }}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </h3>
        <h3 
          style={{ cursor: 'pointer', paddingBottom: '0.5rem', color: activeTab === 'emails' ? 'var(--accent-cyan)' : 'var(--text-secondary)', borderBottom: activeTab === 'emails' ? '2px solid var(--accent-cyan)' : 'none' }}
          onClick={() => setActiveTab('emails')}
        >
          Notification Emails
        </h3>
      </div>

      {loading ? (
        <div style={{color: 'var(--text-secondary)'}}>Loading submissions...</div>
      ) : (
        
        activeTab === 'emails' ? (
          <div style={{display: 'flex', gap: '2rem', flexDirection: 'column'}}>
            <h2>Email Notifications</h2>
            <p style={{ color: 'var(--text-secondary)' }}>These emails will receive a notification whenever a new submission is made.</p>
            
            <div style={{ display: 'flex', gap: '1rem', maxWidth: '500px' }}>
              <input 
                type="email"
                placeholder="email@example.com"
                value={newEmailInput}
                onChange={(e) => setNewEmailInput(e.target.value)}
                style={{ flex: 1, padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-light)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
              />
              <button 
                onClick={addEmail}
                style={{ padding: '0.75rem 1.5rem', borderRadius: '4px', backgroundColor: 'var(--accent-cyan)', color: 'black', border: 'none', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Add Email
              </button>
            </div>
            
            <div style={{ marginTop: '2rem', maxWidth: '500px' }}>
              <h3>Current Recipients</h3>
              {emailsLoading ? <p>Loading...</p> : notificationEmails.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>No emails configured.</p>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {notificationEmails.map(email => (
                    <li key={email} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-secondary)', padding: '0.75rem 1rem', borderRadius: '4px', border: '1px solid var(--border-light)' }}>
                      <span>{email}</span>
                      <button 
                        onClick={() => removeEmail(email)}
                        style={{ background: 'none', border: 'none', color: '#ff4d4f', cursor: 'pointer', textDecoration: 'underline' }}
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ) : activeTab === 'analytics' ? (
        <div style={{display: 'flex', gap: '2rem', flexDirection: 'column'}}>
          <h2>Dashboard Analytics</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
            <div className={styles.uploadBox} style={{ padding: '2rem', textAlign: 'center' }}>
              <h3 style={{ color: 'var(--text-secondary)' }}>Total Submissions</h3>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--accent-cyan)' }}>{submissions.length}</div>
            </div>
            <div className={styles.uploadBox} style={{ padding: '2rem', textAlign: 'center' }}>
              <h3 style={{ color: 'var(--text-secondary)' }}>Total Items Ordered</h3>
              <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--accent-cyan)' }}>
                {submissions.reduce((sum, sub) => sum + sub.items.reduce((s, item) => s + item.qty, 0), 0)}
              </div>
            </div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '1rem' }}>
            <div className={styles.uploadBox} style={{ padding: '1.5rem', cursor: 'default' }}>
              <h3 style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem' }}>Most Popular Items</h3>
              {(() => {
                const itemCounts: Record<string, {name: string, qty: number, code: string}> = {};
                submissions.forEach(sub => {
                  sub.items.forEach(item => {
                    if (!itemCounts[item.code]) {
                      itemCounts[item.code] = { name: item.groupName, qty: 0, code: item.code };
                    }
                    itemCounts[item.code].qty += item.qty;
                  });
                });
                const topItems = Object.values(itemCounts).sort((a, b) => b.qty - a.qty).slice(0, 10);
                return (
                  <ul style={{ listStyle: 'none', padding: 0 }}>
                    {topItems.map((item, idx) => (
                      <li key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--bg-secondary)' }}>
                        <span>{item.name} <span style={{color: 'var(--text-secondary)', fontSize: '0.8rem'}}>({item.code})</span></span>
                        <span style={{ fontWeight: 'bold', color: 'var(--accent-cyan)' }}>{item.qty}</span>
                      </li>
                    ))}
                  </ul>
                );
              })()}
            </div>
            
            <div className={styles.uploadBox} style={{ padding: '1.5rem', cursor: 'default' }}>
              <h3 style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem' }}>Top Hospitals</h3>
              {(() => {
                const hospitalCounts: Record<string, number> = {};
                submissions.forEach(sub => {
                  const h = sub.customer?.hospital || 'Unknown';
                  hospitalCounts[h] = (hospitalCounts[h] || 0) + 1;
                });
                const topHospitals = Object.entries(hospitalCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
                return (
                  <ul style={{ listStyle: 'none', padding: 0 }}>
                    {topHospitals.map(([name, count], idx) => (
                      <li key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--bg-secondary)' }}>
                        <span>{name}</span>
                        <span style={{ fontWeight: 'bold', color: 'var(--accent-cyan)' }}>{count} orders</span>
                      </li>
                    ))}
                  </ul>
                );
              })()}
            </div>
          </div>
        </div>

        ) : (
        <div style={{display: 'flex', gap: '2rem'}}>
          {/* Sidebar list */}
          <div style={{width: '300px', display: 'flex', flexDirection: 'column', gap: '1rem', flexShrink: 0}}>
            <div style={{ display: 'flex', gap: '0.5rem', flexDirection: 'column' }}>
              <input 
                type="text" 
                placeholder="Search by Submission ID..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-light)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', outline: 'none' }}
              />
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button 
                  className={styles.exportBtn} 
                  style={{ marginTop: 0, flex: 1 }}
                  disabled={selectedSubIds.size === 0}
                  onClick={handleBulkExport}
                >
                  Export ({selectedSubIds.size})
                </button>
                <button 
                  className={styles.exportBtn} 
                  style={{ marginTop: 0, flex: 1, backgroundColor: 'var(--accent-red, #ff4444)' }}
                  disabled={selectedSubIds.size === 0}
                  onClick={handleBulkDelete}
                >
                  Delete ({selectedSubIds.size})
                </button>
              </div>
            </div>
            
            {(() => {
              const filteredSubmissions = submissions.filter(s => s.id.toLowerCase().includes(searchQuery.toLowerCase()));
              if (filteredSubmissions.length === 0) {
                return <p style={{color: 'var(--text-muted)'}}>No submissions found.</p>;
              }
              
              const groupedSubmissions = filteredSubmissions.reduce((acc, sub) => {
                const cat = getSubmissionCategory(sub) || 'Unknown';
                if (!acc[cat]) acc[cat] = [];
                acc[cat].push(sub);
                return acc;
              }, {} as Record<string, Submission[]>);

              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {Object.keys(groupedSubmissions).map((catName) => {
                    const subsInCat = groupedSubmissions[catName];
                    const isExpanded = expandedCats[catName];
                    const allSelected = subsInCat.length > 0 && subsInCat.every(s => selectedSubIds.has(s.id));
                    
                    return (
                      <div key={catName} style={{ border: '1px solid var(--border-light)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ display: 'flex', alignItems: 'center', backgroundColor: 'var(--bg-secondary)', padding: '0.75rem' }}>
                          <input 
                            type="checkbox" 
                            checked={allSelected} 
                            onChange={() => toggleCategorySelect(catName, subsInCat)}
                            style={{ marginRight: '0.75rem', transform: 'scale(1.2)', cursor: 'pointer' }}
                          />
                          <div 
                            style={{ flex: 1, fontWeight: 600, cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                            onClick={() => setExpandedCats({ ...expandedCats, [catName]: !isExpanded })}
                          >
                            <span>{catName} ({subsInCat.length})</span>
                            <span>{isExpanded ? '▲' : '▼'}</span>
                          </div>
                        </div>
                        
                        {isExpanded && (
                          <div style={{ padding: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', backgroundColor: 'var(--bg-primary)' }}>
                            {subsInCat.map(sub => (
                              <div 
                                key={sub.id} 
                                className={styles.uploadBox} 
                                style={{ 
                                  padding: '1rem', 
                                  borderColor: selectedSub?.id === sub.id ? 'var(--accent-cyan)' : 'var(--border-light)',
                                  display: 'flex',
                                  alignItems: 'center'
                                }}
                              >
                                <input 
                                  type="checkbox"
                                  checked={selectedSubIds.has(sub.id)}
                                  onChange={(e) => {
                                    const nextSet = new Set(selectedSubIds);
                                    if (e.target.checked) nextSet.add(sub.id);
                                    else nextSet.delete(sub.id);
                                    setSelectedSubIds(nextSet);
                                  }}
                                  style={{ marginRight: '1rem', transform: 'scale(1.2)', cursor: 'pointer' }}
                                />
                                <div style={{ flex: 1, cursor: 'pointer' }} onClick={() => setSelectedSub(sub)}>
                                  <div style={{fontWeight: 600}}>ID: {sub.id.substring(0,6)}...</div>
                                  <div style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
                                    Items: {sub.items.length}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>

          {/* Details */}
          <div style={{flex: 1}}>
            {selectedSub ? (
              <>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
                  <h2>Submission: {selectedSub.id}</h2>
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className={styles.exportBtn} style={{marginTop: 0, padding: '0.5rem 1rem'}} onClick={() => handleExport(selectedSub)}>
                      Export Excel
                    </button>
                    <button className={styles.exportBtn} style={{marginTop: 0, padding: '0.5rem 1rem', backgroundColor: 'var(--accent-red, #ff4444)'}} onClick={() => handleDeleteSubmission(selectedSub.id)}>
                      Delete
                    </button>
                  </div>
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
                  {(() => {
                    const groupedItems = selectedSub.items.reduce((acc, item) => {
                      const key = `${item.categoryName || 'Unknown Category'} > ${item.setName || 'Unknown Set'}`;
                      if (!acc[key]) acc[key] = [];
                      acc[key].push(item);
                      return acc;
                    }, {} as Record<string, CartItem[]>);

                    return Object.keys(groupedItems).map((siteKey, idx) => (
                      <div key={idx} style={{ marginBottom: '2rem' }}>
                        <h4 style={{ color: 'var(--accent-cyan)', marginBottom: '0.75rem', fontSize: '1.1rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.25rem' }}>
                          {siteKey}
                        </h4>
                        <table>
                          <thead>
                            <tr>
                              <th style={{width: '25%'}}>Item Name</th>
                              <th style={{width: '20%'}}>Option Code</th>
                              <th style={{width: '45%'}}>Description</th>
                              <th style={{width: '10%'}}>Qty</th>
                            </tr>
                          </thead>
                          <tbody>
                            {groupedItems[siteKey].map((item, i) => (
                              <tr key={i}>
                                <td>{item.groupName}</td>
                                <td>{item.code}</td>
                                <td>{item.optionDesc}</td>
                                <td>{item.qty}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ));
                  })()}
                </div>
              </>
            ) : (
              <div className={styles.uploadBox} style={{cursor: 'default'}}>
                Select a submission from the left to view details.
              </div>
            )}
          </div>
        </div>
        )
      )}
    </div>
  );
}
