#!/usr/bin/env python3
"""
Parse verse text from Dyczkowski's Tantraloka.
Strategy: verse lines end with (number). Group all lines between verse markers
that don't contain academic apparatus.
"""
import re, os, sys

INPUT_DIR = '/root/projects/tantraloka/site/public/texts-structured/ahnika'
OUTPUT_DIR = '/root/projects/tantraloka/read-clean'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def is_apparatus(line):
    """Check if a line is academic apparatus (footnote, manuscript, etc)."""
    s = line.strip()
    if not s:
        return False
    # Starts with apostrophe
    if s.startswith("'") or s.startswith('\u2018') or s.startswith('\u2019'):
        return True
    # Has academic citation
    if re.search(r'\([A-Z][a-z]+.*?\d{4}.*?\)', s):
        return True
    # Has manuscript reference
    if re.search(r'\bMSs?\b', s):
        return True
    # Is Sanskrit transliteration (no uppercase words, has diacritics)
    if len(s) > 30 and not re.search(r'[A-Z][a-z]{2,}', s) and re.search(r'[āīūṛṝḷḹśṣṅñṭḍṇ]', s):
        return True
    # Page references
    if re.search(r'\b(p\.\s*\d+|pages?\s+\d+)\b', s, re.I) and len(s) < 100:
        return True
    # "There is a play on words here," "He writes:" etc
    if s.startswith(('There is', 'He writes', 'Note that', 'A variant', 'Concerning', 'I have presumed', 'The following couplet')):
        return True
    # Lines about manuscript variants
    if re.search(r'variant|reads|exchanges places', s, re.I) and len(s) < 120:
        return True
    # References to other sections
    if re.search(r'\b(see below|see above|ibid\.|TĀv?\s+\d+/\d+)', s, re.I):
        return True
    return False

def parse_ahnika(filepath):
    with open(filepath) as f:
        lines = f.readlines()
    
    verses = []
    current_verse = []
    in_verse = False
    
    for line in lines:
        s = line.strip()
        if not s:
            continue
        
        # Section heading?
        if re.match(r'^(CHAPTER\s+\w+)', s, re.I) or s in ['TANTRĀLOKA', 'The Introductory Verses', 'The Initial Invocation', 'ABBREVIATIONS']:
            if current_verse:
                verses.append(' '.join(current_verse))
                current_verse = []
            verses.append(f'\n### {s} ###\n')
            in_verse = False
            continue
        
        # Skip apparatus
        if is_apparatus(s):
            if current_verse:
                # Don't append apparatus to verse
                pass
            in_verse = False
            continue
        
        # Check if line ends with verse number
        has_verse_num = re.search(r'\(\d+\)\s*$', s)
        
        if has_verse_num:
            # End of a verse
            current_verse.append(s)
            clean = ' '.join(current_verse)
            clean = re.sub(r'\s*\(\d+\)\s*$', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if clean:
                verses.append(clean)
            current_verse = []
            in_verse = False
        elif re.match(r'^[A-Z]', s) and not re.match(r'^[A-Z][a-z]+:', s):
            # Might be start of verse text
            if not in_verse:
                current_verse = [s]
                in_verse = True
            else:
                current_verse.append(s)
    
    return verses

# Test on ahnika 1
verses = parse_ahnika(os.path.join(INPUT_DIR, '01.txt'))
print(f"Āhnika 1: {len(verses)} verse blocks")
for v in verses[:20]:
    if v.startswith('\n###'):
        print(v)
    else:
        print(f"\n  {v[:150]}")
PYEOF