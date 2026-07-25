#!/usr/bin/env python3
"""Actually clean the text. Strip all scholarly apparatus, keep only the translation."""
import re, os

INPUT = '/root/projects/tantraloka/site/public/texts-structured/ahnika'
OUTPUT = '/root/projects/tantraloka/read-clean'
os.makedirs(OUTPUT, exist_ok=True)

def is_scholarly_apparatus(line):
    """Check if a line is academic apparatus (footnotes, manuscript notes, etc)."""
    s = line.strip()
    if not s:
        return False
    # Lines starting with a digit + period + space (footnote number)
    if re.match(r'^\d+\.\s', s):
        return True
    # Lines referencing manuscript variants
    if re.search(r'MSs?\s+[A-Z]', s) and ('reads' in s or 'variant' in s.lower()):
        return True
    # Lines that are just a single number
    if re.match(r'^\d+$', s):
        return True
    # References to page numbers
    if re.match(r'^pages?\s+\d+', s, re.I):
        return True
    # Lines starting with an apostrophe (footnote continuation)
    if s.startswith("'") and len(s) > 50:
        return True
    # Lines that are just the letter alone (page markers)
    if re.match(r'^[ivxlcdm]+$', s, re.I):
        return True
    # Footnote reference markers at start of line
    if re.match(r'^[\d]+\s', s) and len(s) < 10:
        return True
    return False

def clean_line(line):
    s = line.strip()
    if not s:
        return ''
    
    # Remove leading apostrophe (footnote continuation marker)
    s = re.sub(r"^'\s*", '', s)
    
    # Remove tilde, replace with em-dash
    s = s.replace('~', ' — ')
    
    # Remove inline footnote numbers like (1), (2) anywhere in text
    s = re.sub(r'\s*\(\d+\)\s*', ' ', s)
    
    # Remove superscript footnote markers
    s = re.sub(r'[\u2070-\u209f⁰¹²³⁴⁵⁶⁷⁸⁹ⁱⁿ]+', '', s)
    
    # Remove stray apostrophe at line start
    s = re.sub(r"^'", '', s)
    
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    
    # Remove lines that are just syllable markings like "ii" "iii" etc
    if re.match(r'^[ivxlcdm]+\s*$', s, re.I):
        return ''
    
    return s

def is_actual_content(lines, start_idx):
    """Check if a paragraph is actual content or apparatus."""
    chunk = '\n'.join(lines[max(0,start_idx-1):start_idx+3])
    s = chunk.strip()
    # If it contains manuscript notation, skip
    if re.search(r'MSs?\s+[A-Z]', s) and ('reads' in s or 'variant' in s.lower()):
        return False
    if s.startswith("'") and len(s) > 20:
        return False
    return True

for aid in range(1, 38):
    src = os.path.join(INPUT, f'{aid:02d}.txt')
    if not os.path.exists(src):
        continue
    
    with open(src) as f:
        text = f.read()
    
    lines = text.split('\n')
    cleaned_lines = []
    skip_block = False
    
    for i, line in enumerate(lines):
        s = line.strip()
        
        # Skip scholarly apparatus lines
        if is_scholarly_apparatus(line):
            continue
        
        # Skip lines with manuscript variants (continue until paragraph ends)
        if re.search(r'MSs?\s+[A-Z]', s) and ('reads' in s or 'variant' in s.lower()):
            skip_block = True
            continue
        if skip_block:
            # End of block = empty line
            if not s:
                skip_block = False
            continue
        
        cl = clean_line(line)
        
        # Filter out remaining garbage
        if cl and len(cl) > 3:
            # Skip if it's clearly a footnote (starts with number + period)
            if re.match(r'^\d+\.\s', cl):
                continue
            # Skip pure Sanskrit transliteration lines (transliterated verses)
            if re.match(r'^[a-zāīūṛṝḷḹśṣṅñṭḍṇ\.\,\-\s]+$', cl) and not re.search(r'[A-Z]', cl) and len(cl) > 40:
                # Check if it's mostly consonants (transliterated Sanskrit, not English)
                vowels = sum(1 for c in cl if c in 'aeiouāīūṛṝḷḹ')
                if vowels < len(cl) * 0.25:
                    continue
            cleaned_lines.append(cl)
    
    # Write output
    output = '\n'.join(cleaned_lines)
    outpath = os.path.join(OUTPUT, f'ahnika-{aid:02d}.txt')
    with open(outpath, 'w') as f:
        f.write(output)
    
    words = len(output.split())
    print(f"Āhnika {aid}: {words} words")

# Combined
print("\nCombining...")
all_text = []
for aid in range(1, 38):
    p = os.path.join(OUTPUT, f'ahnika-{aid:02d}.txt')
    if os.path.exists(p):
        with open(p) as f:
            all_text.append(f'=== ĀHNIKA {aid} ===\n\n' + f.read())

combined = '\n\n'.join(all_text)
with open(os.path.join(OUTPUT, 'tantraloka-complete.txt'), 'w') as f:
    f.write(combined)

print(f"Combined: {len(combined.split())} words")
print(f"Written to {OUTPUT}/")
