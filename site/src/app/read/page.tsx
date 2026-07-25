import Link from 'next/link'

const AHNIKAS = [
  { id: 1, title: 'The Types of Liberating Knowledge', subtitle: 'The complete theorem — consciousness, bondage, tattvas, upāyas', verses: '1.1–1.335' },
  { id: 2, title: 'Anupāya', subtitle: 'The meansless penetration — can truth be recognized immediately?', verses: '2.2–2.50' },
  { id: 3, title: 'Paropāya', subtitle: 'The supreme means — the doctrine of reflection', verses: '3.1–3.294' },
  { id: 4, title: 'Śāktopāya', subtitle: 'The empowered means — using thought to undo thought', verses: '4.1–4.279' },
  { id: 5, title: 'Āṇavopāya', subtitle: 'The individual means — body, breath, and support', verses: '5.1–5.160' },
  { id: 6, title: 'Kālopāya', subtitle: 'The temporal means — time as consciousness measured', verses: '6.1–6.241' },
  { id: 7, title: 'Cakrodaya', subtitle: 'The emergence of mantra cycles from the breath', verses: '7.1–7.70' },
  { id: 8, title: 'Deśādhvan', subtitle: 'The path of space — cosmic geography in the body', verses: '8.1–8.249' },
  { id: 9, title: 'Tattvādhvan', subtitle: 'The path of principles — the 36 tattvas in detail', verses: '9.1–9.314' },
  { id: 10, title: 'Tattvabheda', subtitle: 'The division of principles — the seven perceivers', verses: '10.1–10.120' },
  { id: 11, title: 'Kalādhvan', subtitle: 'The path of forces — cosmic eggs and the 38 principles', verses: '11.1–11.118' },
  { id: 12, title: 'Kalādyadhvādhvopayoga', subtitle: 'Application of the path of forces', verses: '12.1–12.25' },
  { id: 13, title: 'Śaktipāta', subtitle: 'The descent of grace — how liberation actually happens', verses: '13.1–13.359' },
  { id: 14, title: 'Dīkṣopakramaṇa', subtitle: 'The preamble to initiation', verses: '14.1–14.46' },
  { id: 15, title: 'Sāmayīdīkṣā', subtitle: 'The common initiation into the rule', verses: '15.1–15.617' },
  { id: 16, title: 'Pautrikī', subtitle: 'Initiation of the apprentice', verses: '16.1–16.311' },
  { id: 17, title: 'Vidheyaprakriyā', subtitle: 'Procedure concerning the apprentice', verses: '17.1–17.122' },
  { id: 18, title: 'Sūkṣmā Dīkṣā', subtitle: 'The brief initiation', verses: '18.1–18.9' },
  { id: 19, title: 'Sadyaḥsamutkrama', subtitle: 'Initiation at the moment of death', verses: '19.1–19.55' },
  { id: 20, title: 'Tulādīkṣā', subtitle: 'Initiation validated by scales', verses: '20.1–20.16' },
  { id: 21, title: 'Pārokṣīdīkṣā', subtitle: 'Initiation of the absent', verses: '21.1–21.61' },
  { id: 22, title: 'Liṅgoddhāra', subtitle: 'Extraction of sectarian marks', verses: '22.1–22.48' },
  { id: 23, title: 'Abhiṣecana', subtitle: 'Consecration of a teacher', verses: '23.1–23.103' },
  { id: 24, title: 'Antyeṣṭi', subtitle: 'Funerary rites', verses: '24.1–24.24' },
  { id: 25, title: 'Śrāddhakḷpti', subtitle: 'Fashioning of ancestral offerings', verses: '25.1–25.29' },
  { id: 26, title: 'Śeṣavṛttinirūpaṇa', subtitle: 'The remaining observance', verses: '26.1–26.65' },
  { id: 27, title: 'Liṅgārcā', subtitle: 'Worship of the liṅga', verses: '27.1–27.59' },
  { id: 28, title: 'Parvan', subtitle: 'Propitious times and occasional rites', verses: '28.1–28.435' },
  { id: 29, title: 'Rahasyacaryā', subtitle: 'The secret Kaula observance', verses: '29.1–29.291' },
  { id: 30, title: 'Mantrasamūha', subtitle: 'The current of mantras', verses: '30.1–30.123' },
  { id: 31, title: 'Trikamaṇḍala', subtitle: 'The Trika maṇḍala', verses: '31.1–31.164' },
  { id: 32, title: 'Mudrikāvidhi', subtitle: 'The procedure concerning seals', verses: '32.1–32.68' },
  { id: 33, title: 'Ekīkāra', subtitle: 'Gathering of the deities into one', verses: '33.1–33.32' },
  { id: 34, title: 'Svasvarūpe Praveśa', subtitle: 'Entry into one\'s own nature', verses: '34.1–34.4' },
  { id: 35, title: 'Śāstramelana', subtitle: 'The encounter of the scriptures', verses: '35.1–35.44' },
  { id: 36, title: 'Āyātikathana', subtitle: 'Account of the transmission', verses: '36.1–36.16' },
  { id: 37, title: 'Śāstropādeyatva', subtitle: 'Description of the scriptures — Abhinavagupta\'s autobiography', verses: '37.1–37.85' },
]

export default function ReadPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Tantrāloka</h1>
      <p className="text-muted text-sm mb-8">37 āhnikas · Dyczkowski translation · guided reading</p>

      <div className="space-y-2">
        {AHNIKAS.map(a => (
          <Link
            key={a.id}
            href={`/read/${a.id}`}
            className="flex items-center gap-4 p-3 rounded-lg border border-ink/5 hover:border-gold/30 hover:bg-white/40 transition-all group"
          >
            <span className="text-gold font-serif text-sm w-16 shrink-0">Day {a.id}</span>
            <div className="flex-1 min-w-0">
              <h2 className="font-semibold text-sm group-hover:text-gold transition-colors truncate">{a.title}</h2>
              <p className="text-xs text-muted truncate">{a.subtitle}</p>
            </div>
            <span className="text-xs text-muted shrink-0">{a.verses}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
