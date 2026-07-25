import TattvaMap from '../../components/TattvaMap'

const SECTIONS = [
  { key: 'pure', label: 'Pure Creation — Śiva through Śuddhavidyā', color: '#ffd700', desc: 'The five pure tattvas — the realm of unity before any subject-object split.' },
  { key: 'maya', label: 'Māyā — The Threshold', color: '#8b0000', desc: 'The power of self-limitation. The one begins to appear as many.' },
  { key: 'kancukas', label: 'Five Kañcukas — The Coverings', color: '#a0522d', desc: 'Time, necessity, attachment, limited knowledge, limited agency.' },
  { key: 'purusa', label: 'Puruṣa & Prakṛti — Subject & Nature', color: '#696969', desc: 'The contracted experiencer and the matrix of manifestation.' },
  { key: 'inner', label: 'Inner Instrument — Buddhi, Ahaṃkāra, Manas', color: '#808080', desc: 'Intellect, ego and mind — the internal cognitive apparatus.' },
  { key: 'senses', label: 'Powers of Perception & Action', color: '#999', desc: 'The five senses of knowledge and five senses of action.' },
  { key: 'tanmatras', label: 'Subtle Elements', color: '#aaa', desc: 'Sound, touch, form, taste, smell — the objects of the senses.' },
  { key: 'elements', label: 'Gross Elements', color: '#bbb', desc: 'Ether, air, fire, water, earth — the material world.' },
]

export default function MapPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">The 36 Tattvas</h1>
      <p className="text-muted mb-6">The vertical structure of manifested experience. Click any principle to study it.</p>
      <div className="bg-white/40 rounded-xl border border-ink/10 p-6 mb-8">
        <TattvaMap />
      </div>
      <div className="space-y-3">
        {SECTIONS.map(s => (
          <div key={s.key} className="flex items-start gap-3">
            <span className="w-3 h-3 rounded mt-1 shrink-0" style={{ backgroundColor: s.color }} />
            <div>
              <p className="text-sm font-medium">{s.label}</p>
              <p className="text-xs text-muted">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
