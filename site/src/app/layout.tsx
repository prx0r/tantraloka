import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Tantrāloka — Study Guide',
  description: 'A visual, audio, hyperlinked study guide to Abhinavagupta\'s Tantrāloka',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <nav className="border-b border-ink/10 bg-white/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6 text-sm">
            <a href="/" className="font-semibold text-gold tracking-wide">Tantrāloka</a>
          <a href="/" className="text-ink/60 hover:text-ink">Home</a>
          <a href="/read" className="text-ink/60 hover:text-ink">Read</a>
          <a href="/map" className="text-ink/60 hover:text-ink">Map</a>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
