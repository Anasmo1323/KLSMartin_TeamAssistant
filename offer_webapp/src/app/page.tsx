'use client';

import { useState, useEffect } from 'react';
import styles from './page.module.css';
import Image from 'next/image';
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
  isStandard?: boolean;
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
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [activeSearchQuery, setActiveSearchQuery] = useState('');
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [mobileCartOpen, setMobileCartOpen] = useState(false);

  // Family Modal State
  const [activeFamilyCode, setActiveFamilyCode] = useState<string | null>(null);
  const [activeFamilyRepCode, setActiveFamilyRepCode] = useState<string | null>(null);
  const [activeFamilyGroupName, setActiveFamilyGroupName] = useState<string | null>(null);
  const [activeFamilyCategoryName, setActiveFamilyCategoryName] = useState<string | null>(null);
  const [activeFamilySetName, setActiveFamilySetName] = useState<string | null>(null);

  // Access Codes & Authentication
  const DISCIPLINE_CODES: Record<string, string> = {
    'Vascular': '4287',
    'CABG': '2317',
    'Thoracic': '9481',
    'Urology': '1910',
    'GS': '6682',
    'Cardio': '8610',
    'ObGyne': '6014',
    'Neuro': '1734',
    'ENT': '2096',
    'ORTHO': '4853'
  };
  const [accessCodeInput, setAccessCodeInput] = useState('');
  const [unlockedDiscipline, setUnlockedDiscipline] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(true);

  // Submission Timer State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitCooldown, setSubmitCooldown] = useState<number>(0);
  const [showOnboarding, setShowOnboarding] = useState<boolean>(false);
  const [onboardingStep, setOnboardingStep] = useState<number>(0);
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  useEffect(() => {
    const savedTheme = localStorage.getItem('kls_theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('kls_theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };


  // Cart State: Record<option_code, CartItem state without qty>
  // We need this so family items added to cart know their group/category context.
  type CartStateEntry = { qty: number, groupName: string, categoryName: string, setName?: string, desc: string };
  const [cartState, setCartState] = useState<Record<string, CartStateEntry>>({});
  const [isLoaded, setIsLoaded] = useState(false);

  const [lightboxImg, setLightboxImg] = useState<string | null>(null);

  // Checkout State
  const [showCheckout, setShowCheckout] = useState(false);
  const [checkoutStep, setCheckoutStep] = useState<0 | 1>(0);
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

  // Handle onboarding logic
  useEffect(() => {
    if (isLoaded && typeof window !== 'undefined') {
      const onboarded = localStorage.getItem('kls_onboarding_done');
      if (onboarded !== 'true') {
        setShowOnboarding(true);
      }
    }
  }, [isLoaded]);

  // Discipline Code matching
  useEffect(() => {
    if (accessCodeInput === '8899') {
      setUnlockedDiscipline('ALL');
      setShowLoginModal(false);
    } else if (accessCodeInput.length === 4) {
      let matched = false;
      for (const [disc, code] of Object.entries(DISCIPLINE_CODES)) {
        if (code === accessCodeInput) {
          setUnlockedDiscipline(disc);
          setShowLoginModal(false);
          matched = true;
          break;
        }
      }
      if (!matched) setUnlockedDiscipline(null);
    } else {
      setUnlockedDiscipline(null);
    }
  }, [accessCodeInput]);

  const openLoginModal = () => {
    setAccessCodeInput('');
    setUnlockedDiscipline(null);
    setShowLoginModal(true);
    setActiveCategory(null);
    setActiveSet(null);
  };

  // Submit button cooldown timer
  useEffect(() => {
    if (submitCooldown > 0) {
      const timer = setTimeout(() => setSubmitCooldown(prev => prev - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      setIsSubmitting(false);
    }
  }, [submitCooldown]);

  // Lock body scroll when any modal or full-screen overlay is open
  useEffect(() => {
    if (mobileCartOpen || activeFamilyCode || showCheckout || lightboxImg || showLoginModal || showOnboarding) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [mobileCartOpen, activeFamilyCode, showCheckout, lightboxImg, showLoginModal, showOnboarding]);

  const updateQty = (opt: Option, delta: number, groupName: string, categoryName: string, setName: string) => {
    setCartState(prev => {
      const cartKey = `${opt.code}|${categoryName}|${setName}|${groupName}`;
      const current = prev[cartKey]?.qty || 0;
      const nextQty = Math.max(0, current + delta);
      const nextState = { ...prev };

      if (nextQty === 0) {
        delete nextState[cartKey];
      } else {
        nextState[cartKey] = {
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

  const updateCartQty = (cartKey: string, delta: number) => {
    setCartState(prev => {
      if (!prev[cartKey]) return prev;
      const nextQty = Math.max(0, prev[cartKey].qty + delta);
      const nextState = { ...prev };
      if (nextQty === 0) {
        delete nextState[cartKey];
      } else {
        nextState[cartKey] = { ...nextState[cartKey], qty: nextQty };
      }
      return nextState;
    });
  };

  const removeCartItem = (cartKey: string) => {
    setCartState(prev => {
      const next = { ...prev };
      delete next[cartKey];
      return next;
    });
  };

  const cartItems = Object.keys(cartState).map(cartKey => {
    const [code] = cartKey.split('|');
    return {
      cartKey,
      code,
      qty: cartState[cartKey].qty,
      groupName: cartState[cartKey].groupName,
      categoryName: cartState[cartKey].categoryName,
      setName: cartState[cartKey].setName,
      optionDesc: cartState[cartKey].desc
    };
  });

  const cartItemsBySite = cartItems.reduce((acc, item) => {
    const siteKey = `${item.categoryName} > ${item.setName}`;
    if (!acc[siteKey]) acc[siteKey] = [];
    acc[siteKey].push(item);
    return acc;
  }, {} as Record<string, typeof cartItems>);

  const totalItems = Object.values(cartState).reduce((a, b) => a + b.qty, 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cartItems.length === 0) return;
    if (!customerDetails.name.trim() || !customerDetails.hospital.trim()) {
      alert("Please fill in the required fields (Name and Hospital).");
      return;
    }
    setIsSubmitting(true);

    try {
      const { db } = await import('../lib/firebase');
      const { collection, addDoc, serverTimestamp } = await import('firebase/firestore');

      const docRef = await addDoc(collection(db, "submissions"), {
          items: cartItems,
          customer: customerDetails,
          timestamp: serverTimestamp(),
          status: 'pending'
        });

        // Trigger email notification asynchronously
        fetch('/api/notify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            submissionId: docRef.id,
            items: cartItems,
            customer: customerDetails,
            totalItems
          })
        }).catch(err => console.error("Email notification failed:", err));

        setCartState({});
      setCustomerDetails({ title: 'Dr.', name: '', hospital: '', phone: '', email: '', notes: '' });
      setShowCheckout(false);
      setMobileCartOpen(false);
      setSubmitCooldown(10);
    } catch (err) {
      console.error("Error submitting order:", err);
      alert("Failed to submit. Please try again.");
      setIsSubmitting(false);
    }
  };

  // Helper to render an option card
  const renderOptionCard = (opt: Option, groupName: string, categoryName: string, setName: string, isFamilyView = false, customKeySuffix?: string) => {
    // If not in family view, we don't know the exact currentQty of the representative item (it could be multiple items in the family selected).
    // Let's aggregate qty for this base_code if not in family view.
    let currentQty = 0;
    if (isFamilyView) {
      const cartKey = `${opt.code}|${categoryName}|${setName}|${groupName}`;
      currentQty = cartState[cartKey]?.qty || 0;
    } else {
      // Sum all quantities for this base_code in this exact location
      currentQty = Object.keys(cartState).filter(k => 
        k.startsWith(`${opt.base_code}`) && k.endsWith(`|${categoryName}|${setName}|${groupName}`)
      ).reduce((sum, k) => sum + cartState[k].qty, 0);
    }
    
    const publicId = (cloudinaryMapping as Record<string, string>)[opt.code];

    const f = opt.extracted_features || {};
    const parts = [];
    if (f.inventor) parts.push(`Inv: ${f.inventor}`);
    if (f.length) parts.push(`${f.length}`);
    if (f.shape) parts.push(`${f.shape}`);
    if (f.dimensions) parts.push(`${f.dimensions}`);
    if (f.tip_type) parts.push(`${f.tip_type}`);
    const featureStr = parts.length > 0 ? parts.join(" | ") : "Standard";

    let borderStyle = opt.isStandard ? '0px solid red' : '1px solid var(--border-light)';
    if (currentQty > 0 && !opt.isStandard) borderStyle = '2px solid var(--accent-cyan)';

    const familyVariationsCount = families[opt.base_code] ? families[opt.base_code].length : 1;

    return (
      <div key={`${categoryName}-${setName}-${groupName}-${opt.code}${customKeySuffix ? "-" + customKeySuffix : ""}`} className={styles.variationCard} style={{
        border: borderStyle,
        position: 'relative',
        boxShadow: currentQty > 0 ? '0 0 12px rgba(0, 200, 255, 0.6)' : 'none',
        backgroundColor: currentQty > 0 ? 'rgba(0, 200, 255, 0.08)' : 'var(--bg-secondary)'
      }}>
        <div className={styles.imagePlaceholder} onClick={() => publicId && setLightboxImg(`https://res.cloudinary.com/pmjavm9d/image/upload/${publicId}.png`)}>
          {publicId ? (
            <Image
              src={`https://res.cloudinary.com/pmjavm9d/image/upload/${publicId}.png`}
              alt={opt.code}
              width={200}
              height={150}
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          ) : (
            <span>No Image</span>
          )}
          <span style={{ display: publicId ? 'none' : 'block' }}></span>
        </div>

        <div className={styles.variationInfo}>
          <span className={styles.variationCode}>{isFamilyView ? opt.code : opt.base_code}</span>
          {opt.details?.description && (
            <span className={styles.variationDesc} style={{ color: 'var(--text-primary)', fontWeight: 500, marginBottom: '0.25rem' }}>
              {opt.details.description}
            </span>
          )}
          <span className={styles.variationDesc}>{featureStr}</span>
          {!isFamilyView && (
            <button
              className={styles.viewFamilyBtn}
              onClick={() => {
                setActiveFamilyCode(opt.base_code);
                setActiveFamilyRepCode(opt.code);
                setActiveFamilyGroupName(groupName);
                setActiveFamilyCategoryName(categoryName);
                setActiveFamilySetName(setName);
              }}
            >
              👁️ View Family & Add to Cart ({familyVariationsCount})
            </button>
          )}
        </div>

        {isFamilyView && (
          <div className={styles.qtySelector}>
            <button className={styles.qtyBtn} onClick={() => updateQty(opt, -1, groupName, categoryName, setName)} disabled={currentQty === 0}>-</button>
            <input type="number" readOnly className={styles.qtyInput} value={currentQty} />
            <button className={styles.qtyBtn} onClick={() => updateQty(opt, 1, groupName, categoryName, setName)}>+</button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={styles.container}>
      {/* Onboarding Overlay */}
      {showOnboarding && (
        <div className={styles.onboardingOverlay}>
          <div className={styles.onboardingModal}>
            <button className={styles.onboardingSkip} onClick={() => {
              localStorage.setItem('kls_onboarding_done', 'true');
              setShowOnboarding(false);
            }}>Skip Tour</button>

            <div className={styles.onboardingContent}>
              {onboardingStep === 0 && (
                <div className={styles.onboardingSlide}>
                  <h2>Welcome to KLSMartin Quick Order!</h2>
                  <p>Start by entering your discipline access code to unlock your specialized instruments.</p>
                  <Image src="/onboarding/login.png" alt="Login Screen" width={700} height={400} style={{ width: "100%", height: "auto" }} />
                </div>
              )}
              {onboardingStep === 1 && (
                <div className={styles.onboardingSlide}>
                  <h2>Explore Categories & Sets</h2>
                  <p>Browse easily. Open categories and explore Internal Sets mapped directly to your workflow.</p>
                  <Image src="/onboarding/navigation.png" alt="Navigation" width={700} height={400} style={{ width: "100%", height: "auto" }} />
                </div>
              )}
              {onboardingStep === 2 && (
                <div className={styles.onboardingSlide}>
                  <h2>Spot the Standards</h2>
                  <p>KLSMartin standard items always appear at the top with a distinct red border.</p>
                  <Image src="/onboarding/standard_items.png" alt="Standard Items" width={700} height={400} style={{ width: "100%", height: "auto" }} />
                </div>
              )}
              {onboardingStep === 3 && (
                <div className={styles.onboardingSlide}>
                  <h2>Review and Submit</h2>
                  <p>Add your quantities and seamlessly finalize your order in the cart.</p>
                  <Image src="/onboarding/checkout.png" alt="Checkout" width={700} height={400} style={{ width: "100%", height: "auto" }} />
                </div>
              )}
            </div>

            <div className={styles.onboardingFooter}>
              <div className={styles.onboardingDots}>
                {[0, 1, 2, 3].map(step => (
                  <span key={step} className={step === onboardingStep ? styles.dotActive : styles.dot}></span>
                ))}
              </div>
              <div className={styles.onboardingActions}>
                {onboardingStep > 0 && (
                  <button className={styles.onboardingBtnSecondary} onClick={() => setOnboardingStep(prev => prev - 1)}>Back</button>
                )}
                {onboardingStep < 3 ? (
                  <button className={styles.onboardingBtnPrimary} onClick={() => setOnboardingStep(prev => prev + 1)}>Next</button>
                ) : (
                  <button className={styles.onboardingBtnPrimary} onClick={() => {
                    localStorage.setItem('kls_onboarding_done', 'true');
                    setShowOnboarding(false);
                  }}>Get Started</button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

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
          <Image src={lightboxImg} alt="Instrument" width={1000} height={800} style={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain', backgroundColor: 'var(--bg-glass)', padding: '2rem', borderRadius: '8px' }} />
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
              <button className={styles.modalClose} onClick={() => {
                setActiveFamilyCode(null);
                setActiveFamilyRepCode(null);
              }}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.variationGrid}>
                {[...families[activeFamilyCode]].sort((a, b) => {
                  if (a.code === activeFamilyRepCode) return -1;
                  if (b.code === activeFamilyRepCode) return 1;
                  return 0;
                }).map((opt, oIdx) =>
                  renderOptionCard(opt, activeFamilyGroupName!, activeFamilyCategoryName!, activeFamilySetName!, true, `fam-${oIdx}`)
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Checkout Modal */}
      {showCheckout && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent} style={{ maxWidth: checkoutStep === 0 ? '1000px' : '500px', width: checkoutStep === 0 ? '90%' : 'auto', maxHeight: checkoutStep === 0 ? '90vh' : 'auto', display: 'flex', flexDirection: 'column' }}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                {checkoutStep === 0 ? 'Review Your Request' : 'Complete Submission'}
              </div>
              <button className={styles.modalClose} onClick={() => setShowCheckout(false)}>✕</button>
            </div>
            <div className={styles.modalBody}>
              {checkoutStep === 0 ? (
                <div>
                  <div style={{ overflowY: 'auto', paddingRight: '1rem', marginBottom: '1rem', flex: 1 }}>
                    {Object.keys(cartItemsBySite).map((siteKey, siteIdx) => (
                      <div key={siteIdx} style={{ marginBottom: '2rem' }}>
                        <h4 style={{ color: 'var(--accent-cyan)', marginBottom: '1rem', fontSize: '1.2rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem' }}>
                          {siteKey}
                        </h4>
                        {cartItemsBySite[siteKey].map((item, idx) => {
                          const publicId = (cloudinaryMapping as Record<string, string>)[item.code];
                          return (
                            <div key={idx} style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', backgroundColor: 'var(--bg-secondary)', padding: '1rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid var(--border-light)' }}>
                              <div style={{ width: '120px', height: '120px', backgroundColor: 'var(--bg-glass)', borderRadius: '8px', padding: '0.5rem', display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
                                {publicId ? (
                                  <Image
                                    src={`https://res.cloudinary.com/pmjavm9d/image/upload/${publicId}.png`}
                                    alt={item.code}
                                    width={100}
                                    height={100}
                                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                                  />
                                ) : (
                                  <span style={{ color: '#ccc', fontSize: '0.8rem' }}>No Image</span>
                                )}
                              </div>
                              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: 'var(--text-primary)' }}>{item.groupName}</div>
                                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Item Code: <span style={{ color: 'var(--accent-cyan)' }}>{item.code}</span></div>
                                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{item.optionDesc}</div>
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '1rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', backgroundColor: 'var(--bg-primary)', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-light)' }}>
                                  <button className={styles.qtyBtn} onClick={() => updateCartQty(item.cartKey, -1)} style={{ padding: '0.25rem 0.75rem' }}>-</button>
                                  <span style={{ minWidth: '30px', textAlign: 'center', fontWeight: 600, fontSize: '1.1rem' }}>{item.qty}</span>
                                  <button className={styles.qtyBtn} onClick={() => updateCartQty(item.cartKey, 1)} style={{ padding: '0.25rem 0.75rem' }}>+</button>
                                </div>
                                <button 
                                  onClick={() => removeCartItem(item.cartKey)}
                                  style={{ background: 'none', border: 'none', color: '#ff4d4f', textDecoration: 'underline', cursor: 'pointer', fontSize: '0.85rem' }}
                                >
                                  Remove
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-light)', paddingTop: '1rem' }}>
                    <h3 style={{ margin: 0 }}>Total Items: {totalItems}</h3>
                    <button 
                      className={styles.submitBtn} 
                      style={{ marginTop: 0, width: 'auto', padding: '0.75rem 2rem' }}
                      onClick={() => setCheckoutStep(1)}
                      disabled={totalItems === 0}
                    >
                      Proceed to Details →
                    </button>
                  </div>
                </div>
              ) : (
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
                    <input required type="text" value={customerDetails.hospital} onChange={e => setCustomerDetails({ ...customerDetails, hospital: e.target.value })} placeholder="e.g. MMC Hospital" />
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
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                    <button type="button" className={styles.qtyBtn} style={{ padding: '0.75rem', width: 'auto' }} onClick={() => setCheckoutStep(0)}>
                      ← Back
                    </button>
                    {totalItems > 0 && (
                      <button type="submit" className={styles.submitBtn} style={{ marginTop: 0, flex: 1 }} disabled={isSubmitting || submitCooldown > 0}>
                        {isSubmitting ? 'Submitting...' : submitCooldown > 0 ? `Submitted! Wait ${submitCooldown}s` : `Submit Request (${totalItems} items)`}
                      </button>
                    )}
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Login Modal Overlay */}
      {showLoginModal && (
        <div className={styles.modalOverlay} style={{ justifyContent: 'center', alignItems: 'center' }}>
          <div className={styles.modalContent} style={{ maxWidth: '400px', width: '90%', padding: '3rem 2rem', textAlign: 'center', margin: 'auto' }}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.8rem' }}>Access Required</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Please enter your 4-digit discipline code to unlock your catalog.</p>
            <input
              type="password"
              maxLength={4}
              value={accessCodeInput}
              onChange={(e) => setAccessCodeInput(e.target.value.replace(/\D/g, ''))}
              style={{ display: 'block', margin: '0 auto', padding: '1rem', borderRadius: '4px', border: '1px solid var(--border-light)', width: '200px', fontSize: '1.5rem', letterSpacing: '0.5rem', outline: 'none', background: 'var(--bg-secondary)', color: 'var(--text-primary)', textAlign: 'center' }}
              placeholder="****"
              autoFocus
            />
            {accessCodeInput.length === 4 && unlockedDiscipline === null && (
              <p style={{ color: 'red', marginTop: '1rem', fontSize: '0.9rem' }}>Invalid code. Please try again.</p>
            )}
          </div>
        </div>
      )}

      <main className={styles.mainContent}>
        <div className={styles.header}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <p className={styles.subtitle} style={{ marginTop: '3rem' }}>Madinaty Medical Centre - Surgical Instrument project</p>
            {!showLoginModal && (
              <button
                onClick={openLoginModal}
                style={{ marginTop: '2.5rem', padding: '0.6rem 1.2rem', borderRadius: '4px', border: '1px solid var(--accent-cyan)', background: 'transparent', color: 'var(--accent-cyan)', cursor: 'pointer', fontWeight: 600 }}
              >
                Enter New Code
              </button>
            )}
          </div>
        </div>

        <div className={styles.navBar}>
          <div style={{ flex: 1, display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span
              className={activeCategory ? styles.navLink : styles.navCurrent}
              onClick={() => { setActiveCategory(null); setActiveSet(null); setExpandedGroup(null); setGlobalSearchQuery(''); setActiveSearchQuery(''); }}
            >
              Disciplines
            </span>
            {activeCategory && (
              <>
                <span className={styles.navSeparator}>/</span>
                <span
                  className={activeSet ? styles.navLink : styles.navCurrent}
                  onClick={() => { setActiveSet(null); setExpandedGroup(null); setGlobalSearchQuery(''); setActiveSearchQuery(''); }}
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
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              placeholder="Search catalog..."
              value={globalSearchQuery}
              onChange={e => setGlobalSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && setActiveSearchQuery(globalSearchQuery)}
              style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: '1px solid var(--border-light)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', outline: 'none', minWidth: '200px' }}
            />
            <button
              onClick={() => setActiveSearchQuery(globalSearchQuery)}
              style={{ padding: '0.5rem 1rem', borderRadius: '4px', border: 'none', backgroundColor: 'var(--accent-cyan)', color: 'black', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Search
            </button>
          </div>
        </div>

        
        
        {activeSearchQuery.trim() !== '' ? (
          <div style={{ display: 'block' }}>
            <h3 style={{ marginBottom: '1rem', color: 'var(--accent-cyan)' }}>Search Results for "{activeSearchQuery}"</h3>
            <div>
              {(() => {
                const q = activeSearchQuery.toLowerCase();
                let hasResults = false;
                const resultsBlock: React.ReactNode[] = [];
                
                categories
                  .filter(cat => unlockedDiscipline === 'ALL' || cat.name === unlockedDiscipline)
                  .forEach(cat => {
                    cat.sets.forEach(set => {
                      const matchedInSet: React.ReactNode[] = [];
                      const seenKeys = new Set<string>();
                      let idxCounter = 0;
                      set.groups.forEach(group => {
                        const deduped = Object.values(group.options.reduce((acc, opt) => {
                          if (!acc[opt.base_code]) acc[opt.base_code] = opt;
                          return acc;
                        }, {} as Record<string, Option>));
                        
                        deduped.forEach(opt => {
                          const match = opt.code.toLowerCase().includes(q) || 
                                        opt.base_code.toLowerCase().includes(q) ||
                                        (opt.basic_description && opt.basic_description.toLowerCase().includes(q)) ||
                                        (opt.details?.description && opt.details.description.toLowerCase().includes(q)) ||
                                        group.group_name.toLowerCase().includes(q);
                          if (match) {
                            const uniqueKey = `${cat.name}-${set.set_name}-${group.group_name}-${opt.code}`;
                            if (!seenKeys.has(uniqueKey)) {
                              seenKeys.add(uniqueKey);
                              matchedInSet.push(renderOptionCard(opt, group.group_name, cat.name, set.set_name, false, `search-${idxCounter++}`));
                            }
                          }
                        });
                      });
                      
                      if (matchedInSet.length > 0) {
                        hasResults = true;
                        resultsBlock.push(
                          <div key={`${cat.name}-${set.set_name}`} style={{ marginBottom: '2rem' }}>
                            <h4 style={{ color: 'var(--text-primary)', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
                              {cat.name} <span style={{ color: 'var(--text-secondary)' }}>/</span> {set.set_name}
                            </h4>
                            <div className={styles.variationGrid}>
                              {matchedInSet}
                            </div>
                          </div>
                        );
                      }
                    });
                  });
                return hasResults ? resultsBlock : <p style={{color: 'var(--text-secondary)'}}>No items found in your unlocked disciplines.</p>;
              })()}
            </div>
          </div>
        ) : (
          <>
            {/* Level 1: Categories */}
        {!activeCategory && (
          <div className={styles.categoryGrid}>
            {categories
              .filter(cat => unlockedDiscipline === 'ALL' || cat.name === unlockedDiscipline)
              .map((cat, idx) => (
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

              const dedupedOptions = Object.values(group.options.reduce((acc, opt) => {
                if (!acc[opt.base_code]) {
                  acc[opt.base_code] = opt;
                }
                return acc;
              }, {} as Record<string, Option>));

              return (
                <div key={gIdx} className={styles.groupItem}>
                  <div
                    className={styles.groupHeader}
                    onClick={() => setExpandedGroup(isExpanded ? null : group.group_id)}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span className={styles.groupTitle}>{group.group_name}</span>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {dedupedOptions.length} core variations
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
                        {dedupedOptions.map((opt, oIdx) => 
                          renderOptionCard(opt, group.group_name, activeCategory!.name, activeSet!.set_name, false, `group-${oIdx}`)
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
          </>
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
            Object.keys(cartItemsBySite).map((siteKey, siteIdx) => (
              <div key={siteIdx} style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ color: 'var(--accent-cyan)', marginBottom: '0.5rem', fontSize: '1rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.25rem' }}>
                  {siteKey}
                </h4>
                {cartItemsBySite[siteKey].map((item, idx) => (
                  <div key={idx} className={styles.cartItem} style={{ marginBottom: '0.5rem' }}>
                    <button className={styles.cartItemRemove} onClick={() => removeCartItem(item.cartKey)}>✕</button>
                    <div className={styles.cartItemHeader}>
                      <span className={styles.cartItemName}>{item.groupName}</span>
                    </div>
                    <div className={styles.cartItemVariation}>
                      <div style={{ color: 'var(--text-primary)', marginBottom: '0.25rem', fontSize: '0.9rem' }}>{item.optionDesc}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                        <span>Code: {item.code}</span>
                        <div className={styles.qtySelector} style={{ width: '110px' }}>
                          <button className={styles.qtyBtn} onClick={() => updateCartQty(item.cartKey, -1)} disabled={item.qty === 0}>-</button>
                          <input type="number" readOnly className={styles.qtyInput} value={item.qty} />
                          <button className={styles.qtyBtn} onClick={() => updateCartQty(item.cartKey, 1)}>+</button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        <button
          className={styles.submitBtn}
          disabled={cartItems.length === 0}
          onClick={() => { setShowCheckout(true); setCheckoutStep(0); }}
          suppressHydrationWarning
        >
          Submit Request
        </button>
      </aside>

      <button className={styles.mobileCartToggle} onClick={() => setMobileCartOpen(true)}>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="28px" height="28px">
          <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z" />
        </svg>
        {totalItems > 0 && <span className={styles.mobileCartBadge}>{totalItems}</span>}
      </button>
    </div>
  );
}
