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
        <header className="main-header">
          <img src="/Technowave.png" alt="Technowave Logo" className="header-logo-technowave" />
          <img src="/kls.png" alt="KLS Martin Logo" className="header-logo-kls" />
        </header>
        {children}
      </body>
    </html>
  )
}
