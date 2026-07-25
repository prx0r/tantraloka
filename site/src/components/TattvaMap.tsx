'use client'
import Link from 'next/link'
import { TattvaNode } from '../types'

const SECTIONS: { key: TattvaNode['section']; label: string; color: string }[] = [
  { key: 'pure', label: 'Pure Creation', color: '#ffd700' },
  { key: 'maya', label: 'Māyā', color: '#8b0000' },
  { key: 'kancukas', label: 'Kañcukas', color: '#a0522d' },
  { key: 'purusa', label: 'Puruṣa', color: '#696969' },
  { key: 'inner', label: 'Inner Instrument', color: '#808080' },
  { key: 'senses', label: 'Senses', color: '#999' },
  { key: 'tanmatras', label: 'Tanmātras', color: '#aaa' },
  { key: 'elements', label: 'Elements', color: '#bbb' },
]

const TATTVAS: TattvaNode[] = [
  { id: 'siva-tattva', label: 'Śiva', sanskrit: 'शिव', slug: 'siva-tattva', level: 0, section: 'pure' },
  { id: 'sakti-tattva', label: 'Śakti', sanskrit: 'शक्ति', level: 0, section: 'pure' },
  { id: 'sadasiva-tattva', label: 'Sadāśiva', sanskrit: 'सदाशिव', level: 0, section: 'pure' },
  { id: 'isvara-tattva', label: 'Īśvara', sanskrit: 'ईश्वर', level: 0, section: 'pure' },
  { id: 'suddhavidya-tattva', label: 'Śuddhavidyā', sanskrit: 'शुद्धविद्या', level: 0, section: 'pure' },
  { id: 'maya', label: 'Māyā', sanskrit: 'माया', slug: 'maya', level: 1, section: 'maya' },
  { id: 'kala-tattva', label: 'Kāla', sanskrit: 'काल', level: 2, section: 'kancukas' },
  { id: 'niyati-tattva', label: 'Niyati', sanskrit: 'नियति', level: 2, section: 'kancukas' },
  { id: 'raga', label: 'Rāga', sanskrit: 'राग', slug: 'raga', level: 2, section: 'kancukas' },
  { id: 'vidya', label: 'Vidyā', sanskrit: 'विद्या', slug: 'vidya', level: 2, section: 'kancukas' },
  { id: 'kala-principle', label: 'Kalā', sanskrit: 'कला', level: 2, section: 'kancukas' },
  { id: 'purusa', label: 'Puruṣa', sanskrit: 'पुरुष', slug: 'purusa', level: 3, section: 'purusa' },
  { id: 'prakriti-tattva', label: 'Prakṛti', sanskrit: 'प्रकृति', level: 3, section: 'purusa' },
  { id: 'buddhi-tattva', label: 'Buddhi', sanskrit: 'बुद्धि', level: 4, section: 'inner' },
  { id: 'ahamkara-tattva', label: 'Ahaṃkāra', sanskrit: 'अहंकार', level: 4, section: 'inner' },
  { id: 'manas-tattva', label: 'Manas', sanskrit: 'मनस्', level: 4, section: 'inner' },
  { id: 'jnanendriyas', label: '5 Jñānendriyas', sanskrit: 'ज्ञानेन्द्रिय', level: 5, section: 'senses' },
  { id: 'karmendriyas', label: '5 Karmendriyas', sanskrit: 'कर्मेन्द्रिय', level: 5, section: 'senses' },
  { id: 'tanmatras', label: '5 Tanmātras', sanskrit: 'तन्मात्र', level: 6, section: 'tanmatras' },
  { id: 'mahabhutas', label: '5 Mahābhūtas', sanskrit: 'महाभूत', level: 7, section: 'elements' },
]

const SECTION_COLORS: Record<string, string> = {
  pure: '#ffd700',
  maya: '#8b0000',
  kancukas: '#a0522d',
  purusa: '#696969',
  inner: '#808080',
  senses: '#999',
  tanmatras: '#aaa',
  elements: '#bbb',
}

export default function TattvaMap({ activeId, studiedIds = [] }: { activeId?: string; studiedIds?: string[] }) {
  const W = 400, H = 42 * TATTVAS.length + 80, COL = 200

  return (
    <div className="w-full overflow-x-auto py-4">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-md mx-auto" style={{ minHeight: 400 }}>
        {TATTVAS.map((t, i) => {
          const y = 50 + i * 38
          const color = SECTION_COLORS[t.section] || '#ccc'
          const isActive = activeId === t.id
          const isStudied = studiedIds.includes(t.id)
          return (
            <g key={t.id}>
              {i < TATTVAS.length - 1 && (
                <line x1={COL} y1={y + 16} x2={COL} y2={y + 38} stroke="#ddd" strokeWidth={1} />
              )}
              {t.slug ? (
                <Link href={`/concepts/${t.slug}`}>
                  <rect
                    x={COL - 70} y={y} width={140} height={24} rx={5}
                    fill={isActive ? color : isStudied ? `${color}30` : '#fff'}
                    stroke={isActive ? color : `${color}40`}
                    strokeWidth={isActive ? 2 : 1}
                    className="cursor-pointer hover:opacity-80 transition-opacity"
                  />
                  <text x={COL} y={y + 16} textAnchor="middle" fill={isActive ? '#fff' : '#1a1a2e'} fontSize="10">
                    {t.label}
                  </text>
                </Link>
              ) : (
                <>
                  <rect x={COL - 70} y={y} width={140} height={24} rx={5} fill="#f5f0e8" stroke="#ddd" strokeWidth={1} />
                  <text x={COL} y={y + 16} textAnchor="middle" fill="#1a1a2e" fontSize="10">{t.label}</text>
                </>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
