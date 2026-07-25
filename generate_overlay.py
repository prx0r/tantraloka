#!/usr/bin/env python3
"""Generate AI overlay for an āhnika: tag passages with type, density, and guided unpacking."""
import json, sys, os, requests

API_KEY = "sk-7dtUVBKJrJcglO9WzdLQZJXwNuz1MucUrDQCZxJjJaH29Q8CqT357DSeFyHV4B75"
API_URL = "https://opencode.ai/zen/go/v1/chat/completions"

def load_text(ahnika_id):
    path = f'/root/projects/tantraloka/site/public/texts/tantraloka-vol{ahnika_id}-dyczkowski.txt'
    if ahnika_id == 1:
        path = '/root/projects/tantraloka/site/public/texts/tantraloka-vol1-dyczkowski.txt'
    elif ahnika_id <= 11:
        path = f'/root/projects/tantraloka/site/public/texts/tantraloka-vol{ahnika_id}-dyczkowski.txt'
    else:
        # For post-volume 11, we'd need combined text
        return None
    
    if not os.path.exists(path):
        # Map by volume ranges
        vol_map = {1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8,9:9,10:10,11:11,12:7,13:7,14:7,
                   15:8,16:9,17:9,18:9,19:9,20:9,21:9,22:9,23:9,24:9,25:9,26:9,27:9,
                   28:10,29:10,30:11,31:11,32:11,33:11,34:11,35:11,36:11,37:11}
        vol = vol_map.get(ahnika_id, 1)
        path = f'/root/projects/tantraloka/site/public/texts/tantraloka-vol{vol}-dyczkowski.txt'
    
    with open(path) as f:
        return f.read()

def chunk_text(text, max_chars=6000):
    """Split text into chunks for API processing."""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) < max_chars:
            current += p + '\n\n'
        else:
            if current.strip():
                chunks.append(current.strip())
            current = p + '\n\n'
    if current.strip():
        chunks.append(current.strip())
    return chunks

def overlay_prompt(text_chunk):
    return f"""You are analyzing Abhinavagupta's Tantrāloka (Dyczkowski translation + Jayaratha commentary).

Tag each paragraph in the text below. For each paragraph, output a JSON object with:
- "text": first 80 chars of paragraph
- "type": "core_teaching" (direct verse translation/doctrinal claim), "explanation" (unfolding what it means), "scholarly_note" (academic discussion), "commentary" (Jayaratha), "dense" (complex argument needing unpacking)
- "density": 0.1 (easy) to 1.0 (very dense)
- "ai_unpack": if density > 0.5, a one-sentence plain-language explanation of what this passage means
- "speaker": "dyczkowski_translation", "dyczkowski_note", "jayaratha", or "sanskrit"
- "goldrender_scene": if applicable, the best matching scene from: luminous_bindu, pulse_field, paired_spiral, descending_canopy, radiant_field, balanced_triads, veil_grid, constriction_rings, contracted_subject, guna_loom, triptych_psychology, sense_lotus, action_chain, subtle_qualities, five_elements, full_descent, ascent_return, body_cosmogram, mirror_macro_micro, closing_seal

Text:
{text_chunk}

Return ONLY a JSON array of objects. No other text."""

def generate_overlay(ahnika_id):
    text = load_text(ahnika_id)
    if not text:
        print(f"Could not load text for āhnika {ahnika_id}")
        return
    
    # Find the actual start (skip front matter for vol 1)
    if ahnika_id == 1:
        # Start from first verse content
        idx = text.find('vimalakalā')
        if idx > 0:
            text = text[idx:]
    
    chunks = chunk_text(text, 5000)
    all_paragraphs = []
    
    print(f"Processing āhnika {ahnika_id}: {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        try:
            r = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-v4-flash",
                    "messages": [{"role": "user", "content": overlay_prompt(chunk)}],
                    "max_tokens": 4000,
                    "temperature": 0.2
                },
                timeout=120
            )
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                # Extract JSON array from response
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                parsed = json.loads(content)
                all_paragraphs.extend(parsed)
                print(f"    Got {len(parsed)} paragraphs")
            else:
                print(f"    Error: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"    Exception: {e}")
    
    # Save overlay
    outdir = '/root/projects/tantraloka/site/src/content/overlays'
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, f'ahnika-{ahnika_id:02d}.json')
    with open(outpath, 'w') as f:
        json.dump(all_paragraphs, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(all_paragraphs)} paragraph tags to {outpath}")

if __name__ == '__main__':
    ahnika_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    generate_overlay(ahnika_id)
