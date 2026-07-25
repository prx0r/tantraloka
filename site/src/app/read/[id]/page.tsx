import Reader from './Reader'

const AHNIKA_VOL_MAP: Record<number, number> = {
  1:1, 2:2, 3:2, 4:3, 5:4, 6:4, 7:5, 8:5, 9:6, 10:6,
  11:7, 12:7, 13:7, 14:7, 15:8, 16:9, 17:9, 18:9, 19:9,
  20:9, 21:9, 22:9, 23:9, 24:9, 25:9, 26:9, 27:9,
  28:10, 29:10, 30:11, 31:11, 32:11, 33:11, 34:11, 35:11, 36:11, 37:11
}

export function generateStaticParams() {
  return Array.from({length: 37}, (_, i) => ({id: (i + 1).toString()}))
}

export default function Page({ params }: { params: { id: string } }) {
  const id = Number(params.id)
  const vol = AHNIKA_VOL_MAP[id] || 1
  return <Reader ahnikaId={id} volume={vol} />
}
