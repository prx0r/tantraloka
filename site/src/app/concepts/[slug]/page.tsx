import { Concept } from '../../../types'
import ExploreView from '../../../components/ExploreView'
import { notFound } from 'next/navigation'

async function getData(slug: string) {
  const ids = ['prakasha-vimarsha', 'spanda', 'maya', 'vidya', 'raga', 'kancukas', 'purusa']
  try {
    const concept: Concept = (await import(`../../../content/concepts/${slug}.json`)).default
    const allConcepts: Concept[] = []
    for (const id of ids) {
      try { allConcepts.push((await import(`../../../content/concepts/${id}.json`)).default) } catch {}
    }
    return { concept, allConcepts }
  } catch { return null }
}

export async function generateStaticParams() {
  return ['prakasha-vimarsha', 'spanda', 'maya', 'vidya', 'raga', 'kancukas', 'purusa'].map(s => ({ slug: s }))
}

export default async function Page(props: { params: Promise<{ slug: string }> }) {
  const params = await props.params
  const data = await getData(params.slug)
  if (!data) notFound()
  return <ExploreView concept={data.concept} allConcepts={data.allConcepts} />
}
