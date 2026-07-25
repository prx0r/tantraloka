#!/usr/bin/env python3
"""
Extract only verse translations from Dyczkowski's Tantraloka.
Pattern identified from manual reading of Day 1:
- Section headings (CHAPTER ONE, etc.) are dividers
- Verse text flows across multiple lines and ends with (1), (2), etc.
- Everything between verse end-markers is apparatus (footnotes, commentary, variants)
"""
import re, os, sys

INPUT_DIR = '/root/projects/tantraloka/site/public/texts-structured/ahnika'
OUTPUT_DIR = '/root/projects/tantraloka/read-clean'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_verses(text):
    lines = text.split('\n')
    output = []
    verse_buffer = []
    in_verse = False
    in_apparatus = False
    
    for line in lines:
        s = line.strip()
        if not s:
            continue
        
        # Section heading?
        if re.match(r'^(CHAPTER\s+\w+)', s, re.I) or s in ['TANTRĀLOKA', 'ABBREVIATIONS']:
            if verse_buffer:
                output.append(('verse', ' '.join(verse_buffer)))
                verse_buffer = []
            output.append(('section', s))
            in_verse = False
            in_apparatus = False
            continue
        
        # Does this line end with a verse number?
        verse_match = re.search(r'\((\d+)\)\s*$', s)
        # Also check for double-bracket verse endings like || 1 I|
        alt_verse = re.search(r'\|\|\s*\d+\s*[I]*\s*\|', s)
        
        if verse_match:
            verse_num = int(verse_match.group(1))
            # This ends a verse
            if in_verse:
                verse_buffer.append(s)
                clean = ' '.join(verse_buffer)
                # Remove the trailing (n)
                clean = re.sub(r'\s*\(\d+\)\s*$', '', clean)
                output.append(('verse', clean))
                verse_buffer = []
                in_verse = False
            else:
                # Single-line verse
                clean = re.sub(r'\s*\(\d+\)\s*$', '', s)
                output.append(('verse', clean))
                in_verse = False
            in_apparatus = False
            continue
        
        elif alt_verse:
            # Alternative verse ending (Sanskrit style)
            clean = s
            output.append(('verse', clean))
            in_verse = False
            in_apparatus = False
            continue
        
        # Check if this line starts apparatus
        if s.startswith("'") or s.startswith('\u2018') or s.startswith('\u2019'):
            in_apparatus = True
            continue
        
        # Check for citation patterns
        if re.search(r'\([A-Z][a-z]+.*?\d{4}.*?\)', s):
            in_apparatus = True
            continue
        if re.search(r'\bMSs?\b', s):
            in_apparatus = True
            continue
        
        # Check if line is Sanskrit transliteration (diacritics, no English words)
        if len(s) > 20 and not re.search(r'[A-Z][a-z]{2,}', s) and re.search(r'[āīūṛṝḷḹśṣṅñṭḍṇ]', s):
            in_apparatus = True
            continue
        
        # If in apparatus, skip
        if in_apparatus:
            continue
        
        # This line might be verse text
        if not in_verse:
            in_verse = True
            verse_buffer = [s]
        else:
            verse_buffer.append(s)
    
    # Flush remaining
    if verse_buffer:
        output.append(('verse', ' '.join(verse_buffer)))
    
    return output

# Process all files
for aid in range(1, 38):
    src = os.path.join(INPUT_DIR, f'{aid:02d}.txt')
    if not os.path.exists(src):
        continue
    with open(src) as f:
        text = f.read()
    
    result = extract_verses(text)
    
    # Write clean text
    clean_lines = []
    for typ, content in result:
        if typ == 'section':
            clean_lines.append(f'\n{content}\n{"-" * 40}\n')
        else:
            # Clean up the verse text
            content = content.replace('~', '—')
            content = re.sub(r'\s+', ' ', content).strip()
            clean_lines.append(content)
    
    output = '\n\n'.join(clean_lines)
    outpath = os.path.join(OUTPUT_DIR, f'ahnika-{aid:02d}-verses.txt')
    with open(outpath, 'w') as f:
        f.write(output)
    
    print(f"Āhnika {aid}: {len(result)} items, {len(output.split())} words")

# Verify Āhnika 1
print("\n=== FIRST 15 ITEMS OF ĀHNIKA 1 ===")
with open(os.path.join(OUTPUT_DIR, 'ahnika-01-verses.txt')) as f:
    content = f.read()
items = content.split('\n\n')
for item in items[:15]:
    print(f"\n  {item[:150]}")
