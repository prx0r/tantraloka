#!/usr/bin/env python3
"""
Final formatting pass: structured, TTS-clean text files per ahnika.
No garbage, no inline references, proper section hierarchy.
"""
import re, os

INPUT_DIR = '/root/projects/tantraloka/site/public/texts-structured/ahnika'
OUTPUT_DIR = '/root/projects/tantraloka/read'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_for_tts(text):
    """Remove anything that would make TTS stumble."""
    lines = text.split('\n')
    cleaned = []
    
    for line in lines:
        s = line.strip()
        if not s:
            cleaned.append('')
            continue
        
        # Remove page number lines (just digits)
        if re.match(r'^\d+$', s):
            continue
        
        # Remove footnote references like (1), (2), etc at end of lines  
        s = re.sub(r'\s*\(\d+\)\s*$', '', s)
        
        # Remove inline footnote markers
        s = re.sub(r'[\u2070-\u209f⁰¹²³⁴⁵⁶⁷⁸⁹ⁱⁿ]+', '', s)
        
        # Remove bullet markers used for footnotes
        s = re.sub(r'^[\d]+\.\s+', '', s)
        
        # Fix spacing around em-dashes
        s = s.replace('–', '—')
        s = re.sub(r'\s+—\s+', ' — ', s)
        
        # Remove lone punctuation lines
        if re.match(r'^[\s\-\—\.\,\;\:\!\?]+$', s):
            continue
        
        # Collapse multiple spaces
        s = re.sub(r'\s+', ' ', s).strip()
        
        # Remove leading/trailing special chars
        s = s.strip('·•*†‡')
        
        if s:
            cleaned.append(s)
    
    return '\n'.join(cleaned)

def format_ahnika(text, ahnika_num):
    """Format ahnika text with clear structure."""
    # Clean first
    text = clean_for_tts(text)
    
    lines = text.split('\n')
    formatted = []
    
    # Opening header
    formatted.append(f'')
    formatted.append(f'ĀHNIKA {ahnika_num}')
    formatted.append(f'{"=" * 60}')
    formatted.append('')
    
    in_header = True
    for i, line in enumerate(lines):
        s = line.strip()
        
        # Detect section headings
        if re.match(r'^(CHAPTER|Chapter)\s+\w+', s):
            if not in_header:
                formatted.append('')
            formatted.append(s.upper())
            formatted.append('-' * 50)
            formatted.append('')
            in_header = False
            continue
        
        # Detect subsection headings (like "Section 1:")
        if re.match(r'^(Section|SECTION)\s+\d+', s) or re.match(r'^[A-Z][a-z]+.*:\s*$', s):
            formatted.append('')
            formatted.append(s)
            formatted.append('')
            in_header = False
            continue
        
        # Skip repetitive copyright/acknowledgment text that wasn't caught
        if any(word in s.lower() for word in ['all rights reserved', 'isbn', 'www.anuttaratrika']):
            continue
        
        if s:
            formatted.append(s)
            in_header = False
        else:
            if not in_header:
                formatted.append('')
    
    return '\n'.join(formatted)

# Process all 37 ahnikas
for aid in range(1, 38):
    src = os.path.join(INPUT_DIR, f'{aid:02d}.txt')
    if not os.path.exists(src):
        print(f"Missing: Āhnika {aid}")
        continue
    
    with open(src) as f:
        text = f.read()
    
    formatted = format_ahnika(text, aid)
    
    dst = os.path.join(OUTPUT_DIR, f'ahnika-{aid:02d}.txt')
    with open(dst, 'w') as f:
        f.write(formatted)
    
    words = len(formatted.split())
    print(f"Āhnika {aid}: {words} words -> {dst}")

# Also create a combined file
print("\nCreating combined file...")
combined = []
for aid in range(1, 38):
    src = os.path.join(OUTPUT_DIR, f'ahnika-{aid:02d}.txt')
    if os.path.exists(src):
        with open(src) as f:
            combined.append(f.read())

combined_path = os.path.join(OUTPUT_DIR, 'tantraloka-complete.txt')
with open(combined_path, 'w') as f:
    f.write('\n\n'.join(combined))

total_words = sum(len(c.split()) for c in combined)
print(f"\nCombined: {total_words} words across 37 ahnikas")
print(f"\nFiles written to {OUTPUT_DIR}/")
print("Read with any text editor or TTS app.")
