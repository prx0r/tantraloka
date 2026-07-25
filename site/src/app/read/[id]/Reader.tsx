'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'

const AHNIKA_INFO: Record<number, { title: string; subtitle: string }> = {
  1: { title: 'Vijñānābhid', subtitle: 'The Types of Liberating Knowledge' },
  2: { title: 'Anupāya', subtitle: 'The Meansless Penetration' },
  3: { title: 'Paropāya', subtitle: 'The Supreme Means' },
  4: { title: 'Śāktopāya', subtitle: 'The Empowered Means' },
  5: { title: 'Āṇavopāya', subtitle: 'The Individual Means' },
  6: { title: 'Kālopāya', subtitle: 'The Temporal Means' },
  7: { title: 'Cakrodaya', subtitle: 'The Emergence of Mantra Cycles' },
  8: { title: 'Deśādhvan', subtitle: 'The Path of Space' },
  9: { title: 'Tattvādhvan', subtitle: 'The Path of Principles' },
  10: { title: 'Tattvabheda', subtitle: 'The Division of Principles' },
  11: { title: 'Kalādhvan', subtitle: 'The Path of Forces' },
  12: { title: 'Kalādyadhvādhvopayoga', subtitle: 'Application of the Path' },
  13: { title: 'Śaktipātatirohitī', subtitle: 'Descents of Power and Obscuration' },
  14: { title: 'Dīkṣopakramaṇa', subtitle: 'Preamble to Initiation' },
  15: { title: 'Sāmayīdīkṣā', subtitle: 'The Common Initiation' },
  16: { title: 'Pautrikī', subtitle: 'Initiation of the Apprentice' },
  17: { title: 'Vidheyaprakriyā', subtitle: 'Procedure for the Apprentice' },
  18: { title: 'Sūkṣmā Dīkṣā', subtitle: 'The Brief Initiation' },
  19: { title: 'Sadyaḥsamutkrama', subtitle: 'Initiation at Death' },
  20: { title: 'Tulādīkṣā', subtitle: 'Initiation by Scales' },
  21: { title: 'Pārokṣīdīkṣā', subtitle: 'Initiation of the Absent' },
  22: { title: 'Liṅgoddhāra', subtitle: 'Extraction of Sectarian Marks' },
  23: { title: 'Abhiṣecana', subtitle: 'Consecration of a Teacher' },
  24: { title: 'Antyeṣṭi', subtitle: 'Funerary Rites' },
  25: { title: 'Śrāddhakḷpti', subtitle: 'Ancestral Offerings' },
  26: { title: 'Śeṣavṛttinirūpaṇa', subtitle: 'The Remaining Observance' },
  27: { title: 'Liṅgārcā', subtitle: 'Worship of the Liṅga' },
  28: { title: 'Parvan', subtitle: 'Propitious Times & Occasional Rites' },
  29: { title: 'Rahasyacaryā', subtitle: 'The Secret Kaula Observance' },
  30: { title: 'Mantrasamūha', subtitle: 'The Current of Mantras' },
  31: { title: 'Trikamaṇḍala', subtitle: 'The Trika Maṇḍala' },
  32: { title: 'Mudrikāvidhi', subtitle: 'Procedure Concerning Seals' },
  33: { title: 'Ekīkāra', subtitle: 'Gathering of the Deities' },
  34: { title: 'Svasvarūpe Praveśa', subtitle: 'Entry into One\'s Own Nature' },
  35: { title: 'Śāstramelana', subtitle: 'The Encounter of Scriptures' },
  36: { title: 'Āyātikathana', subtitle: 'Account of the Transmission' },
  37: { title: 'Śāstropādeyatva', subtitle: 'The Scriptures to be Adopted' },
}

export default function Reader({ ahnikaId, volume }: { ahnikaId: number; volume: number }) {
  const [text, setText] = useState('')
  const [showToc, setShowToc] = useState(true)
  const [showNotes, setShowNotes] = useState(false)
  const [scrollProgress, setScrollProgress] = useState(0)
  const textRef = useRef<HTMLDivElement>(null)
  const info = AHNIKA_INFO[ahnikaId] || { title: '', subtitle: '' }

  useEffect(() => {
    fetch(`/texts/ahnika/${String(ahnikaId).padStart(2, '0')}.txt`)
      .then(r => r.text())
      .then(setText)
      .catch(() => {
        fetch(`/texts/tantraloka-vol${volume}-dyczkowski.txt`)
          .then(r2 => r2.text())
          .then(setText)
          .catch(() => setText('Failed to load text.'))
      })
  }, [ahnikaId, volume])

  useEffect(() => {
    const saved = localStorage.getItem(`scroll-${ahnikaId}`)
    if (saved && textRef.current) {
      textRef.current.scrollTop = parseInt(saved)
    }
  }, [text, ahnikaId])

  const handleScroll = useCallback(() => {
    if (textRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = textRef.current
      setScrollProgress(scrollTop / (scrollHeight - clientHeight))
      localStorage.setItem(`scroll-${ahnikaId}`, String(scrollTop))
    }
  }, [ahnikaId])

  const paragraphs = text.split('\n\n').filter(p => p.trim())

  return (
    <div className="flex h-[calc(100vh-3.5rem)] -mx-4">
      {/* Left TOC */}
      <div className={`${showToc ? 'w-56' : 'w-0'} border-r border-ink/10 overflow-hidden transition-all duration-200 shrink-0 bg-white/40`}>
        <div className="p-3 space-y-0.5 overflow-y-auto h-full text-sm">
          <p className="text-xs text-muted uppercase tracking-wider mb-2 px-2">37 Āhnikas</p>
          {Array.from({length: 37}, (_, i) => i + 1).map(id => {
            const a = AHNIKA_INFO[id]
            return (
              <Link
                key={id}
                href={`/read/${id}/`}
                className={`block px-2 py-1 rounded text-xs transition-colors ${
                  id === ahnikaId ? 'bg-gold/10 text-gold font-medium' : 'text-ink/70 hover:bg-ink/5'
                }`}
              >
                <span className="text-muted mr-1.5 w-5 inline-block text-right">{id}.</span>
                {a?.title || `Āhnika ${id}`}
              </Link>
            )
          })}
        </div>
      </div>

      {/* Center */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-5 py-2 border-b border-ink/10 bg-white/60 shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={() => setShowToc(!showToc)} className="text-xs text-muted hover:text-ink px-1">
              {showToc ? '◀' : '▶'}
            </button>
            <div>
              <p className="text-xs text-muted leading-tight">Āhnika {ahnikaId}</p>
              <h1 className="text-sm font-semibold leading-tight">{info.title}</h1>
            </div>
          </div>
          <button onClick={() => setShowNotes(!showNotes)} className="text-xs text-muted hover:text-ink">
            Notes {showNotes ? '▶' : '◀'}
          </button>
        </div>

        {/* Text */}
        <div ref={textRef} onScroll={handleScroll} className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-8 py-8 font-serif leading-relaxed text-[15px] text-ink/85">
            {paragraphs.map((p, i) => {
              const isSanskrit = /[āīūṛṝḷḹśṣṅñṭḍṇ]/.test(p) && p.length < 200
              const isShort = p.length < 60
              return (
                <p key={i} className={`mb-3 ${
                  isSanskrit ? 'text-center text-gold/60 text-sm tracking-wider' : ''
                } ${
                  isShort && !isSanskrit ? 'text-sm text-ink/60' : ''
                }`}>
                  {p}
                </p>
              )
            })}
          </div>
        </div>

        {/* Progress */}
        <div className="h-0.5 bg-ink/5 shrink-0">
          <div className="h-full bg-gold/50 transition-all duration-300" style={{ width: `${Math.min(scrollProgress, 1) * 100}%` }} />
        </div>
      </div>

      {/* Right Notes */}
      <div className={`${showNotes ? 'w-64' : 'w-0'} border-l border-ink/10 overflow-hidden transition-all duration-200 shrink-0 bg-white/40`}>
        <div className="p-4 text-sm overflow-y-auto h-full">
          <p className="text-xs text-muted uppercase tracking-wider mb-3">Notes</p>
          <p className="text-xs text-ink/60 italic">Jayaratha commentary and Dyczkowski&apos;s footnotes for the current passage will appear here.</p>
        </div>
      </div>
    </div>
  )
}
