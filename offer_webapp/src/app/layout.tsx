import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'KLS Martin - Interactive Offer',
  description: 'Select surgical instruments from the offer catalog.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <header style={{
          backgroundColor: '#111111',
          borderBottom: '4px solid var(--accent-main)',
          padding: '1rem 2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: '80px'
        }}>
          <img src="/Technowave.png" alt="Technowave Logo" style={{ maxHeight: '180%', objectFit: 'contain' }} />
          <img src="/kls.png" alt="KLS Martin Logo" style={{ maxHeight: '500%', objectFit: 'contain' }} />
        </header>
        {children}
      </body>
    </html>
  )
}
