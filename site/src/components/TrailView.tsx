'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Trail, Concept } from '../types'

export default function TrailView({ trail, conceptMap }: { trail: Trail; conceptMap: Record<string, Concept> }) {
  const [step, setStep] = useState(0)
  const s = trail.steps[step]
  const c = s ? conceptMap[s.conceptId] : null

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <p className="text-xs text-muted uppercase tracking-wide mb-1">Guided Lesson</p>
        <h1 className="text-2xl font-bold mb-2">{trail.title}</h1>
        <p className="text-muted">{trail.description}</p>
      </div>

      {/* Progress bar */}
      <div className="flex gap-1 mb-6">
        {trail.steps.map((_, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? 'bg-gold' : 'bg-ink/10'}`}
          />
        ))}
      </div>

      {c && (
        <div className="concept-card">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-gold font-serif text-sm">{c.sanskrit}</p>
              <h2 className="text-lg font-bold">{c.title}</h2>
            </div>
            <Link href={`/concepts/${s.conceptId}`} className="text-xs text-gold hover:text-rust shrink-0">
              Full page →
            </Link>
          </div>

          <div className="bg-white/60 rounded-lg p-4 mb-3">
            <p className="text-xs text-muted uppercase tracking-wide mb-1">Intuitive</p>
            <p className="text-sm italic">{c.intuitiveMeaning}</p>
          </div>

          <div className="bg-ink/[0.02] border border-ink/5 rounded-lg p-4 mb-4">
            <p className="text-xs text-muted uppercase tracking-wide mb-1">Narration</p>
            <p className="text-sm leading-relaxed">{s.narration}</p>
          </div>

          {s.reflectionPrompt && (
            <div className="bg-parchment/80 rounded-lg p-4 border border-gold/20">
              <p className="text-xs text-rust uppercase tracking-wide mb-1">Reflection</p>
              <p className="text-sm italic text-ink/80">{s.reflectionPrompt}</p>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-6">
        <button
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
          className="px-4 py-2 border border-ink/20 rounded-lg text-sm disabled:opacity-30 hover:bg-white/50 transition-colors"
        >
          ← Previous
        </button>
        <span className="text-sm text-muted">{step + 1} / {trail.steps.length}</span>
        <button
          onClick={() => setStep(Math.min(trail.steps.length - 1, step + 1))}
          disabled={step === trail.steps.length - 1}
          className="px-4 py-2 bg-gold text-white rounded-lg text-sm disabled:opacity-30 hover:bg-rust transition-colors"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
