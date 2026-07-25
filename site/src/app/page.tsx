import Link from 'next/link'
import { Concept } from '../types'
import TattvaMap from '../components/TattvaMap'

async function getConcepts(): Promise<Concept[]> {
  const ids = ['prakasha-vimarsha', 'spanda', 'maya', 'vidya', 'raga', 'kancukas', 'purusa']
  const concepts: Concept[] = []
  for (const id of ids) {
    try { concepts.push((await import(`../content/concepts/${id}.json`)).default) } catch {}
  }
  return concepts
}

export default async function Home() {
  const concepts = await getConcepts()

  return (
    <div>
      <section className="mb-12">
        <h1 className="text-3xl font-bold mb-2">Tantrāloka</h1>
        <p className="text-muted text-lg max-w-2xl">
          A visual, hyperlinked study guide to Abhinavagupta's <em>Light on and of the Tantras</em>.
        </p>
      </section>

      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">The 36 Tattvas</h2>
          <Link href="/map" className="text-sm text-gold hover:text-rust">Full map →</Link>
        </div>
        <div className="bg-white/40 rounded-xl border border-ink/10 p-4">
          <TattvaMap studiedIds={concepts.map(c => c.id)} />
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Explore Concepts</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {concepts.map(c => (
            <Link key={c.id} href={`/concepts/${c.id}`} className="concept-card block group">
              <p className="text-gold font-serif text-sm mb-1">{c.sanskrit}</p>
              <h3 className="font-semibold text-lg mb-2 group-hover:text-gold transition-colors">{c.title}</h3>
              <p className="text-sm text-muted line-clamp-3">{c.summary}</p>
              <div className="flex flex-wrap gap-1 mt-3">
                {c.tags.slice(0, 3).map(t => <span key={t} className="px-2 py-0.5 bg-ink/5 rounded text-xs text-muted">{t}</span>)}
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Guided Lessons</h2>
        <Link href="/lessons/infinity-to-individual" className="concept-card block group">
          <h3 className="font-semibold text-lg mb-2 group-hover:text-gold transition-colors">How Infinity Becomes Finite</h3>
          <p className="text-sm text-muted">6-step journey from pure consciousness through Māyā and the five coverings to individual awareness.</p>
          <div className="flex gap-2 mt-3">
            <span className="px-2 py-0.5 bg-ink/5 rounded text-xs text-muted">6 steps</span>
            <span className="px-2 py-0.5 bg-ink/5 rounded text-xs text-muted">Guided</span>
          </div>
        </Link>
      </section>
    </div>
  )
}
