'use client';

import { useState, useEffect } from 'react';
import styles from './page.module.css';
import catalogData from '../data/offer_catalog.json';
import cloudinaryMapping from '../data/cloudinary_mapping.json';
import familyCatalog from '../data/family_catalog.json';

type Option = {
  option_id?: string;
  code: string;
  base_code: string;
  basic_description: string;
  qty?: number | null;
  image_url?: string | null;
  extracted_features?: any;
  details?: any;
};

type Group = {
  group_id: string;
  group_name: string;
  required_qty: number;
  options: Option[];
};

type InternalSet = {
  set_id: string;
  set_name: string;
  groups: Group[];
};

type Category = {
  name: string;
  sets: InternalSet[];
};

type CartItem = {
  groupName: string;
  optionDesc: string;
  qty: number;
  code: string;
  categoryName: string;
  setName?: string;
};

export default function Home() {
  const categories = catalogData as Category[];
  const families = familyCatalog as Record<string, Option[]>;

  // Navigation State
  const [activeCategory, setActiveCategory] = useState<Category | null>(null);
  const [activeSet, setActiveSet] = useState<InternalSet | null>(null);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [mobileCartOpen, setMobileCartOpen] = useState(false);

  // Family Modal State
  const [activeFamilyCode, setActiveFamilyCode] = useState<string | null>(null);
  const [activeFamilyGroupName, setActiveFamilyGroupName] = useState<string | null>(null);
  const [activeFamilyCategoryName, setActiveFamilyCategoryName] = useState<string | null>(null);
  const [activeFamilySetName, setActiveFamilySetName] = useState<string | null>(null);

  // Cart State: Record<option_code, CartItem state without qty>
  // We need this so family items added to cart know their group/category context.
  type CartStateEntry = { qty: number, groupName: string, categoryName: string, setName?: string, desc: string };
  const [cartState, setCartState] = useState<Record<string, CartStateEntry>>({});
  const [isLoaded, setIsLoaded] = useState(false);

  const [lightboxImg, setLightboxImg] = useState<string | null>(null);

  // Checkout State
  const [showCheckout, setShowCheckout] = useState(false);
  const [customerDetails, setCustomerDetails] = useState({ title: 'Dr.', name: '', hospital: '', phone: '', email: '', notes: '' });

  // Load cart from LocalStorage on mount
  useEffect(() => {
    const savedCart = localStorage.getItem('kls_cart');
    if (savedCart) {
      try { setCartState(JSON.parse(savedCart)); } catch (e) { }
    }
    setIsLoaded(true);
  }, []);

  // Save cart to LocalStorage on change
  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem('kls_cart', JSON.stringify(cartState));
    }
  }, [cartState, isLoaded]);

  // Lock body scroll when any modal or full-screen overlay is open
  useEffect(() => {
    if (mobileCartOpen || activeFamilyCode || showCheckout || lightboxImg) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [mobileCartOpen, activeFamilyCode, showCheckout, lightboxImg]);

  const updateQty = (opt: Option, delta: number, groupName: string, categoryName: string, setName: string) => {
    setCartState(prev => {
      const current = prev[opt.code]?.qty || 0;
      const nextQty = Math.max(0, current + delta);
      const nextState = { ...prev };

      if (nextQty === 0) {
        delete nextState[opt.code];
      } else {
        nextState[opt.code] = {
          qty: nextQty,
          groupName,
          categoryName,
          setName,
          desc: opt.basic_description
        };
      }
      return nextState;
    });
  };

  const updateCartQty = (code: string, delta: number) => {
    setCartState(prev => {
      if (!prev[code]) return prev;
      const nextQty = Math.max(0, prev[code].qty + delta);
      const nextState = { ...prev };
      if (nextQty === 0) {
        delete nextState[code];
      } else {
        nextState[code] = { ...nextState[code], qty: nextQty };
      }
      return nextState;
    });
  };

  const removeCartItem = (optionCode: string) => {
    setCartState(prev => {
      const next = { ...prev };
      delete next[optionCode];
      return next;
    });
  };

  const cartItems: CartItem[] = Object.keys(cartState).map(code => ({
    code,
    qty: cartState[code].qty,
    groupName: cartState[code].groupName,
    categoryName: cartState[code].categoryName,
    setName: cartState[code].setName,
    optionDesc: cartState[code].desc
  }));

  const totalItems = Object.values(cartState).reduce((a, b) => a + b.qty, 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cartItems.length === 0) return;
    if (!customerDetails.name.trim() || !customerDetails.hospital.trim()) {
      alert("Please provide your Name and Hospital.");
      return;
    }

    try {
      const { db } = await import('../lib/firebase');
      const { collection, addDoc, serverTimestamp } = await import('firebase/firestore');

      const docRef = await addDoc(collection(db, "submissions"), {
        customer: customerDetails,
        items: cartItems,
        timestamp: serverTimestamp(),
        status: "pending"
      });

      alert(`Offer submitted successfully! Reference ID: ${docRef.id}`);
      setCartState({});
      setCustomerDetails({ title: 'Dr.', name: '', hospital: '', phone: '', email: '', notes: '' });
      setShowCheckout(false);
      setMobileCartOpen(false);
    } catch (error) {
      console.error("Error submitting offer: ", error);
      alert("Failed to submit the offer. Please check your connection.");
    }
  };

  // Helper to render an option card
  const renderOptionCard = (opt: Option, groupName: string, categoryName: string, setName: string, isFamilyView = false) => {
    const currentQty = cartState[opt.code]?.qty || 0;
    const publicId = (cloudinaryMapping as Record<string, string>)[opt.code];

    const f = opt.extracted_features || {};
    const parts = [];
    if (f.inventor) parts.push(`Inv: ${f.inventor}`);
    if (f.length) parts.push(`${f.length}`);
    if (f.shape) parts.push(`${f.shape}`);
    if (f.dimensions) parts.push(`${f.dimensions}`);
    if (f.tip_type) parts.push(`${f.tip_type}`);
    const featureStr = parts.length > 0 ? parts.join(" | ") : "Standard";

    return (
      <div key={opt.code} className={styles.variationCard} style={{ borderColor: currentQty > 0 ? 'var(--accent-cyan)' : 'var(--border-light)' }}>
        <div className={styles.imagePlaceholder} onClick={() => publicId && setLightboxImg(`https://res.cloudinary.com/pmjavm9d/image/upload/${publicId}.png`)}>
          {publicId ? (
            <img
              src={`https://res.cloudinary.com/pmjavm9d/image/upload/${publicId}.png`}
              alt={opt.code}
              onError={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextElementSibling!.textContent = 'No Image Found'; }}
            />
          ) : (
            <span>No Image</span>
          )}
          <span style={{ display: publicId ? 'none' : 'block' }}></span>
        </div>

        <div className={styles.variationInfo}>
          <span className={styles.variationCode}>{opt.code}</span>
          <span className={styles.variationDesc}>{featureStr}</span>
          {!isFamilyView && families[opt.base_code] && families[opt.base_code].length > 1 && (
            <button
              className={styles.viewFamilyBtn}
              onClick={() => {
                setActiveFamilyCode(opt.base_code);
                setActiveFamilyGroupName(groupName);
                setActiveFamilyCategoryName(categoryName);
                setActiveFamilySetName(setName);
              }}
            >
              👁️ View Family ({families[opt.base_code].length})
            </button>
          )}
        </div>

        <div className={styles.qtySelector}>
          <button className={styles.qtyBtn} onClick={() => updateQty(opt, -1, groupName, categoryName, setName)} disabled={currentQty === 0}>-</button>
          <input type="number" readOnly className={styles.qtyInput} value={currentQty} />
          <button className={styles.qtyBtn} onClick={() => updateQty(opt, 1, groupName, categoryName, setName)}>+</button>
        </div>
      </div>
    );
  };

  return (
    <div className={styles.container}>
      {/* Lightbox */}
      {lightboxImg && (
        <div
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.9)', zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'zoom-out'
          }}
          onClick={() => setLightboxImg(null)}
        >
          <img src={lightboxImg} alt="Instrument" style={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain', backgroundColor: 'white', padding: '2rem', borderRadius: '8px' }} />
        </div>
      )}

      {/* Family Modal */}
      {activeFamilyCode && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                Family <span>{activeFamilyCode}</span>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 'normal', marginTop: '0.25rem' }}>
                  {activeFamilyCategoryName} &gt; {activeFamilyGroupName}
                </div>
              </div>
              <button className={styles.modalClose} onClick={() => setActiveFamilyCode(null)}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.variationGrid}>
                {families[activeFamilyCode].map(opt =>
                  renderOptionCard(opt, activeFamilyGroupName!, activeFamilyCategoryName!, activeFamilySetName!, true)
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Checkout Modal */}
      {showCheckout && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent} style={{ maxWidth: '500px' }}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>Complete Submission</div>
              <button className={styles.modalClose} onClick={() => setShowCheckout(false)}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <form onSubmit={handleSubmit} className={styles.checkoutForm}>
                <label>
                  Doctor / Rep Name *
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <select 
                      value={customerDetails.title} 
                      onChange={e => setCustomerDetails({ ...customerDetails, title: e.target.value })}
                      style={{ padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)', background: 'var(--bg-primary)', color: 'var(--text-primary)', outline: 'none' }}
                    >
                      <option value="Dr.">Dr.</option>
                      <option value="Mr.">Mr.</option>
                      <option value="Eng.">Eng.</option>
                      <option value="Ms.">Ms.</option>
                    </select>
                    <input required type="text" style={{ flex: 1 }} value={customerDetails.name} onChange={e => setCustomerDetails({ ...customerDetails, name: e.target.value })} placeholder="e.g. Ahmed" />
                  </div>
                </label>
                <label>
                  Hospital / Clinic *
                  <input required type="text" value={customerDetails.hospital} onChange={e => setCustomerDetails({ ...customerDetails, hospital: e.target.value })} placeholder="e.g. MCC Hospital" />
                </label>
                <label>
                  Phone Number (Optional)
                  <input type="tel" value={customerDetails.phone} onChange={e => setCustomerDetails({ ...customerDetails, phone: e.target.value })} placeholder="01xx xxx xxxx" />
                </label>
                <label>
                  Contact Email (Optional)
                  <input type="email" value={customerDetails.email} onChange={e => setCustomerDetails({ ...customerDetails, email: e.target.value })} placeholder="email@example.com" />
                </label>
                <label>
                  Additional Notes (Optional)
                  <textarea rows={3} value={customerDetails.notes} onChange={e => setCustomerDetails({ ...customerDetails, notes: e.target.value })} placeholder="Any specific requirements..."></textarea>
                </label>
                {totalItems > 0 && (
                  <button className={styles.submitBtn} onClick={() => setShowCheckout(true)} style={{ marginTop: '2rem' }}>
                    Submit Request ({totalItems} items)
                  </button>
                )}</form>
            </div>
          </div>
        </div>
      )}

      <main className={styles.mainContent}>
        <div className={styles.header}>
          <p className={styles.subtitle} style={{marginTop: '1rem'}}>Browse disciplines and select your specific instrument variations.</p>
        </div>

        <div className={styles.navBar}>
          <span
            className={activeCategory ? styles.navLink : styles.navCurrent}
            onClick={() => { setActiveCategory(null); setActiveSet(null); setExpandedGroup(null); }}
          >
            All Disciplines
          </span>
          {activeCategory && (
            <>
              <span className={styles.navSeparator}>/</span>
              <span
                className={activeSet ? styles.navLink : styles.navCurrent}
                onClick={() => { setActiveSet(null); setExpandedGroup(null); }}
              >
                {activeCategory.name}
              </span>
            </>
          )}
          {activeSet && (
            <>
              <span className={styles.navSeparator}>/</span>
              <span className={styles.navCurrent}>{activeSet.set_name}</span>
            </>
          )}
        </div>

        {/* Level 1: Categories */}
        {!activeCategory && (
          <div className={styles.categoryGrid}>
            {categories.map((cat, idx) => (
              <div
                key={idx}
                className={styles.categoryCard}
                onClick={() => setActiveCategory(cat)}
              >
                <h3>{cat.name}</h3>
                <p>{cat.sets.length} Subsets</p>
              </div>
            ))}
          </div>
        )}

        {/* Level 2: Internal Sets */}
        {activeCategory && !activeSet && (
          <div className={styles.categoryGrid}>
            {activeCategory.sets.map((set, idx) => {
              // Calculate how many items are selected in this specific set
              const selectedInSet = set.groups.reduce((setSum, group) => {
                return setSum + group.options.reduce((sum, opt) => sum + (cartState[opt.code]?.qty || 0), 0);
              }, 0);

              return (
                <div
                  key={idx}
                  className={styles.categoryCard}
                  onClick={() => setActiveSet(set)}
                  style={{ borderColor: selectedInSet > 0 ? 'var(--accent-cyan)' : 'var(--border-light)' }}
                >
                  <h3>{set.set_name}</h3>
                  <p>{set.groups.length} Instrument Types</p>
                  {selectedInSet > 0 && <span style={{ color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>★ {selectedInSet} items in cart</span>}
                </div>
              )
            })}
          </div>
        )}

        {/* Level 3: Groups (Accordions) inside Internal Set */}
        {activeSet && (
          <div className={styles.groupList}>
            {activeSet.groups.map((group, gIdx) => {
              const isExpanded = expandedGroup === group.group_id;

              const selectedInGroup = Object.values(cartState)
                .filter(item => item.groupName === group.group_name && item.categoryName === activeCategory!.name)
                .reduce((sum, item) => sum + item.qty, 0);

              return (
                <div key={gIdx} className={styles.groupItem}>
                  <div
                    className={styles.groupHeader}
                    onClick={() => setExpandedGroup(isExpanded ? null : group.group_id)}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span className={styles.groupTitle}>{group.group_name}</span>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {group.options.length} core variations
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      {selectedInGroup > 0 && (
                        <span className={styles.groupBadge}>{selectedInGroup} Selected</span>
                      )}
                      <span>{isExpanded ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className={styles.groupContent}>
                      <div className={styles.variationGrid}>
                        {group.options.map(opt => renderOptionCard(opt, group.group_name, activeCategory!.name, activeSet!.set_name))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>

      <aside className={`${styles.sidebar} glass-panel ${mobileCartOpen ? styles.mobileOpen : ''}`}>
        <div className={styles.sidebarTitle}>
          <span>Selected Items</span>
          {mobileCartOpen && (
            <span style={{ cursor: 'pointer', fontSize: '1rem', color: 'var(--text-secondary)' }} onClick={() => setMobileCartOpen(false)}>✕ Close</span>
          )}
          {!mobileCartOpen && <span className={styles.cartTotal}>{totalItems} total</span>}
        </div>

        <div className={styles.cartItems}>
          {cartItems.length === 0 ? (
            <div className={styles.emptyCart}>No items selected yet.</div>
          ) : (
            cartItems.map((item, idx) => (
              <div key={idx} className={styles.cartItem}>
                <button className={styles.cartItemRemove} onClick={() => removeCartItem(item.code)}>✕</button>
                <div className={styles.cartItemHeader}>
                  <span className={styles.cartItemName}>{item.groupName}</span>
                </div>
                <div className={styles.cartItemVariation}>
                  <div style={{ color: 'var(--text-primary)', marginBottom: '0.25rem', fontSize: '0.9rem' }}>{item.optionDesc}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                    <span>Code: {item.code}</span>
                    <div className={styles.qtySelector} style={{ width: '110px' }}>
                      <button className={styles.qtyBtn} onClick={() => updateCartQty(item.code, -1)} disabled={item.qty === 0}>-</button>
                      <input type="number" readOnly className={styles.qtyInput} value={item.qty} />
                      <button className={styles.qtyBtn} onClick={() => updateCartQty(item.code, 1)}>+</button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <button
          className={styles.submitBtn}
          disabled={cartItems.length === 0}
          onClick={() => setShowCheckout(true)}
          suppressHydrationWarning
        >
          Submit Request
        </button>
      </aside>

      <button className={styles.mobileCartToggle} onClick={() => setMobileCartOpen(true)}>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="28px" height="28px">
          <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>
        </svg>
        {totalItems > 0 && <span className={styles.mobileCartBadge}>{totalItems}</span>}
      </button>
    </div>
  );
}
