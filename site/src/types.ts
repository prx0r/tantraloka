export type RelationType =
  | 'manifests_as'
  | 'contracts_into'
  | 'liberated_as'
  | 'presupposes'
  | 'opposes'
  | 'used_in_practice'
  | 'explained_by'
  | 'appears_in_chapter'
  | 'analogy_of'

export interface TypedRelation {
  targetId: string
  type: RelationType
  label?: string
}

export interface Hotspot {
  id: string
  x: number
  y: number
  type: 'explanation' | 'concept' | 'source' | 'practice' | 'relation'
  targetId?: string
  label: string
  panelContent?: string
}

export interface SourcePassage {
  work: string
  chapter: string
  verse?: string
  sanskrit?: string
  transliteration?: string
  translation: string
  wordNotes?: string
  commentary?: string
}

export interface Concept {
  id: string
  title: string
  sanskrit: string
  transliteration: string
  summary: string
  intuitiveMeaning: string
  explanation: string
  image: string
  plateHotspots?: Hotspot[]
  sourcePassages: SourcePassage[]
  relations: TypedRelation[]
  trails: string[]
  audio?: string
  tags: string[]
}

export interface TrailStep {
  conceptId: string
  narration: string
  reflectionPrompt?: string
}

export interface Trail {
  id: string
  title: string
  description: string
  steps: TrailStep[]
}

export interface TattvaNode {
  id: string
  label: string
  sanskrit: string
  slug?: string
  level: number
  section: 'pure' | 'maya' | 'kancukas' | 'purusa' | 'inner' | 'senses' | 'tanmatras' | 'elements'
}
