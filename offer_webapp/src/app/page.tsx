'use client';

import React from 'react';
import styles from './page.module.css';

export default function Home() {
  return (
    <div className={styles.container} style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <main className={styles.mainContent} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
        <h1 style={{ fontSize: '3rem', marginBottom: '2rem', color: 'var(--text-primary)' }}>
          Welcome to <span style={{ color: 'var(--accent-blue)' }}>Technowave</span>
        </h1>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 4rem auto', lineHeight: '1.6' }}>
          Providing state-of-the-art surgical instruments and biomedical solutions. Please access your dedicated catalog via your custom link.
        </p>

        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '2.5rem', borderRadius: '12px', border: '1px solid var(--border-light)', width: '100%', maxWidth: '600px', textAlign: 'left' }}>
          <h2 style={{ color: 'var(--accent-red, #ff4d4f)', fontSize: '1.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.75rem' }}>
            Our Team
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Team Member 1 */}
            <div>
              <div style={{ color: '#000000ff', fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                Eng. Albear Emil
              </div>
              <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                Sales and Project Manager
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                +20 106 664 0171 | <a href="mailto:albear@technowave-eg.com" style={{ color: 'var(--accent-cyan)' }}>albear@technowave-eg.com</a>
              </div>
            </div>

            {/* Team Member 2 */}
            <div>
              <div style={{ color: '#000000ff', fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                Eng. Anas Mohamed
              </div>
              <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                Biomedical Sales Engineer
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                +20 103 755 5936 | <a href="mailto:amohamed@technowave-eg.com" style={{ color: 'var(--accent-cyan)' }}>amohamed@technowave-eg.com</a>
              </div>
            </div>

            {/* Team Member 3 */}
            <div>
              <div style={{ color: '#000000ff', fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                Eng. Abdelrahman Hegazy
              </div>
              <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                Biomedical Sales Engineer
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                +20 103 755 5897 | <a href="mailto:asalah@technowave-eg.com" style={{ color: 'var(--accent-cyan)' }}>asalah@technowave-eg.com</a>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
