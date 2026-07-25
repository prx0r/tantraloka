'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Concept } from '../types'

export default function ExploreView({ concept, allConcepts }: { concept: Concept; allConcepts: Concept[] }) {
  const [activeHotspot, setActiveHotspot] = useState<string | null>(null)
  const [mode, setMode] = useState<'intuitive' | 'scholarly'>('intuitive')

  const hs = concept.plateHotspots || []
  const activeHs = hs.find(h => h.id === activeHotspot)

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* Plate area */}
      <div className="flex-1 relative bg-white/60 rounded-xl border border-ink/10 overflow-hidden" style={{ minHeight: 500 }}>
        <div className="absolute inset-0 flex items-center justify-center text-muted/30 text-sm">
          [Plate: {concept.title}]
        </div>
        {hs.map(h => (
          <button
            key={h.id}
            onClick={() => setActiveHotspot(activeHotspot === h.id ? null : h.id)}
            style={{ left: `${h.x}%`, top: `${h.y}%` }}
            className="absolute w-5 h-5 -ml-2.5 -mt-2.5 rounded-full bg-gold/80 border-2 border-white shadow-md hover:scale-125 transition-transform z-10"
            title={h.label}
          />
        ))}
        {activeHotspot && activeHs && (
          <div className="absolute bottom-4 left-4 right-4 bg-white/95 backdrop-blur rounded-lg border border-ink/10 p-4 shadow-lg z-20">
            <div className="flex items-start justify-between gap-2 mb-1">
              <span className="text-xs text-gold uppercase tracking-wide font-semibold">{activeHs.type}</span>
              <button onClick={() => setActiveHotspot(null)} className="text-muted hover:text-ink">&times;</button>
            </div>
            <p className="font-semibold text-sm mb-1">{activeHs.label}</p>
            {activeHs.panelContent && <p className="text-sm text-ink/70">{activeHs.panelContent}</p>}
            {activeHs.targetId && (
              <Link href={`/concepts/${activeHs.targetId}`} className="text-xs text-gold hover:text-rust mt-2 inline-block">
                Open concept →
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Side panel */}
      <div className="lg:w-80 shrink-0">
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setMode('intuitive')}
            className={`px-3 py-1 text-xs rounded-full ${mode === 'intuitive' ? 'bg-gold text-white' : 'bg-ink/5 text-muted'}`}
          >
            Intuitive
          </button>
          <button
            onClick={() => setMode('scholarly')}
            className={`px-3 py-1 text-xs rounded-full ${mode === 'scholarly' ? 'bg-gold text-white' : 'bg-ink/5 text-muted'}`}
          >
            Scholarly
          </button>
        </div>

        <p className="text-gold font-serif mb-1">{concept.sanskrit}</p>
        <h2 className="text-xl font-bold mb-2">{concept.title}</h2>
        <p className="text-sm text-muted italic mb-4">{concept.transliteration}</p>

        <p className="text-sm text-ink/80 mb-4 leading-relaxed">
          {mode === 'intuitive' ? concept.intuitiveMeaning : concept.explanation}
        </p>

        {concept.relations.length > 0 && (
          <div className="mb-4">
            <p className="text-xs text-muted uppercase tracking-wide font-semibold mb-2">Relations</p>
            <ul className="space-y-1">
              {concept.relations.map((r, i) => {
                const target = allConcepts.find(c => c.id === r.targetId)
                return (
                  <li key={i}>
                    <Link href={`/concepts/${r.targetId}`} className="text-sm text-gold hover:text-rust">
                      {r.type.replace('_', ' ')} → {target?.title || r.targetId}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        <div className="flex gap-2">
          {concept.trails.map(t => (
            <Link key={t} href={`/lessons/${t}`} className="px-3 py-1 text-xs border border-gold/30 text-gold rounded-full hover:bg-gold/5">
              Trail: {t.replace(/-/g, ' ')}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
