import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ThemeToggle from './ThemeToggle'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'TechnoWave - Interactive Technical Offer List',
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
        <header className="main-header">
          <img src="/Technowave.png" alt="Technowave Logo" className="header-logo-technowave" />
          <div style={{ display: 'flex', alignItems: 'center', height: '100%', gap: '1rem' }}>
            <img src="/kls.png" alt="KLS Martin Logo" className="header-logo-kls" />
          </div>
        </header>
        {children}
      </body>
    </html>
  )
}
