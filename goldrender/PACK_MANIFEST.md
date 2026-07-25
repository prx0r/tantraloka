# Tantrāloka Pack Master Manifest

## Visual Style Groups

### Group: White Scientific Field (most packs)
Clean ivory field, structured diagrams, concept-led color, sparse typography.

| Pack | Scenes | Status | Essay Matched |
|------|--------|--------|---------------|
| awareness_not_inside_predicts | 4 ⚠️ stub | registered | 03_awareness_is_not_inside |
| body_remembers_idea | 7 | registered | 05_a_body_may_remember |
| borrowed_voices | 14 | registered | 04_universe_speaks_borrowed |
| breath_clock_brain | 9 | registered | 05_breath_is_the_clock |
| cells_solving_problem | 4 ⚠️ stub | registered | 05_your_cells_may_be_solving |
| diagram_becomes_alive | 4 ⚠️ stub | registered | 03_a_diagram_becomes_alive |
| embryo_flashes_brain | 8 | registered | 02_embryo_flashes |
| form_needs_no_form | 24 | registered | 05_form_needs_a_place |
| grace_breaks_the_law | 22 | registered | 01_grace_breaks_the_law |
| knowledge_binds | 18 / 55 | both | 01_knowledge_binds |
| leaf_uses_noise | 4 ⚠️ stub | registered | 05_a_leaf_uses_noise |
| life_crosses_barriers | 54 ✅ | registered + uploaded | 01_life_crosses_barriers |
| look_outward_heart | 7 | registered | 01_look_outward |
| matter_remembers_gods | 7 | registered | 03_matter_remembers_gods |
| music_medicine | 9 | registered | 03_music_is_medicine |
| nature_builds_bodies | 4 ⚠️ stub | registered | 03_nature_builds_bodies |
| organism_survives_predicting | 4 ⚠️ stub | registered | 02_organism_survives |
| part_never_entered_body | 9 | registered | 03_part_of_you_never_entered |
| sakti_draws_line | 23 | registered | 05_sakti_draws_the_line |
| self_world_upright | 23 | registered | 04_self_and_world |
| senses_eating_universe | 4 ⚠️ stub | registered | 02_your_senses |
| soul_needs_second_body | 16 | registered | 03_soul_needs_second_body |
| symbol_becomes_real | 23 | registered | 04_symbol_becomes_real |
| whole_acts_before_parts | 6 | registered | 05_whole_can_act |
| universe_hiding_in_attention | 25 | registered | 01_universe_is_hiding |
| voice_existed_before_language | 13 | registered | 01_your_voice_existed |

### Group: Alchemical / Manuscript
Ivory, gold leaf, Devanagari, manuscript aesthetics.

| Pack | Scenes | Status | Style |
|------|--------|--------|-------|
| dead_buried_instructions | 20 | registered | Orphic gold tablets, underworld |
| fire_not_destroying | 45 | registered | Alchemical: nigredo, tria prima, crucible |
| goddess_path_alphabet | 15 | registered | Sanskrit alphabet, Malini, matrka |

### Group: Theophanic / Mirror
Parchment-white, gold/silver/rose, face mirrors.

| Pack | Scenes | Status | Style |
|------|--------|--------|-------|
| god_looks_through_your_face | 49 | registered | Ibn Arabi, hidden treasure, mirror |

### Group: Biomedical / Morphology
Body maps, bioelectric fields, cellular processes.

| Pack | Scenes | Status | Style |
|------|--------|--------|-------|
| voice_inside_chest | 40 | registered | Enteric brain, serotonin, vagus |

---

## Large Packs from R2 — NOT in goldrender/ Pipeline
These are full 55-164 scene packs on R2, need to be integrated.

| Pack | Scenes | Style | Priority |
|------|--------|-------|----------|
| a_bird_may_see_magnetic_field | 128 | Geomagnetic / cryptochrome / bird navigation | ⭐ high |
| a_markov_blanket | 116 | Free energy principle, active inference | ⭐ high |
| an_organism_survives_predicting | 115 | Predictive processing, regulation | ⭐ high |
| a_tumor_may_be_a_cell | 112 | Bioelectric, cancer as forgetfulness | ⭐ high |
| body_diagram | 58 | Body schema, interoception | medium |
| body_remembers_shape | 63 | Planarian regeneration, morphogenesis | ⭐ high |
| infinite_had_to_become_hungry | 73 | Consciousness → hunger → life | medium |
| self_two_moments | 57 | Self as continuity across time | medium |
| the_whole_can_act_before_parts | 129 | Downward causation, embryogenesis | ⭐ high |
| world_arrives_before_name | 61 | Pre-categorical field, naming | medium |
| world_learns_to_feel | 56 | Boundary → sensation → emotion → empathy | medium |
| your_cells_solving_problem_you | 164 | Morphogenesis as navigation | ⭐ high |
| your_senses_eating_universe | 99 | Sensory fire, digestion metaphor | medium |

---

## Dashboard Status

| Video | Status | MP4 | Needs |
|-------|--------|-----|-------|
| life-crosses-barriers | review | ✅ | — |
| expansion-essay1 | review | ✅ | — |
| 01-k4 → 10-hellenistic-tantra | draft | ❌ | Render + upload |
| 04-tattvas | draft | ❌ | Has render in R2, needs dashboard registration |

---

## Recommendations

### Immediate
1. **Register** the 15 R2 packs in `goldrender/` batch pipeline (copy from `platinum essays/`)
2. **Create tier mapping** for new packs based on essaylist.md priority
3. **Wire `04-tattvas`** to dashboard (already rendered in R2)

### Render Priority
1. **Large packs with narration** (life_crosses already done as proof)
2. **Full packs** (40+ scenes: god_looks, fire_not_destroying, voice_inside_chest)
3. **R2 packs** with highest essay priority (birds, markov blanket, organism, tumor, body_remembers_shape, whole_act, cells_solving)
4. **Stubs** need real content (7 packs with 4 scenes each)
5. **Dashboard drafts** (10 blog essays 01-k4 through 10-hellenistic)

### Infrastructure
- All packs need: narration/ dir with edge-tts WAVs, contact sheet, timeline
- Upload to `blog-video-assets/renders/{slug}/` + register on dashboard
- Dashboard auto-selects first video with MP4
