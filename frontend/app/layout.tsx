import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Marchiol Pricing Cockpit',
  description: 'Strumento di raccomandazione sconti per agenti Marchiol',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body className={inter.className}>
        <header className="sticky top-0 z-50 border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-3 shadow-sm">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-sm">M</span>
          </div>
          <span className="font-semibold text-gray-900 tracking-tight">
            Marchiol Pricing Cockpit
          </span>
          <span className="ml-auto text-xs text-gray-400 font-mono">prototype M2</span>
        </header>
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  )
}
