#!/usr/bin/env python3
"""
Proper parser for Dyczkowski's Tantraloka translation.
Separates: verse translation | footnotes | Jayaratha commentary | manuscript variants
"""
import re, os

INPUT = '/root/projects/tantraloka/site/public/texts-structured/ahnika/01.txt'
OUTPUT = '/root/projects/tantraloka/read-clean'

with open(INPUT) as f:
    lines = f.readlines()

# Patterns
FOOTNOTE_START = re.compile(r"^['\u2018]")  # Starts with apostrophe or smart quote
CITATION = re.compile(r'\([A-Z][a-z]+.*?\d{4}.*?\)')  # (Author Year: ...)
MANUSCRIPT = re.compile(r'\bMSs?\b\.?\s*[A-Z]')  # MS G, MSs G and Ch
SANSKRIT_BLOCK = re.compile(r'^[a-zāīūṛṝḷḹśṣṅñṭḍṇ\.\,\-\|\s\[\]\(\)\:\d]+$')  # Mostly lowercase + diacritics
VERSE_END = re.compile(r'\(\d+\)\s*$')  # Ends with (1), (2) etc
PAGE_REF = re.compile(r'\b(p\.\s*\d+|pages?\s+\d+)\b', re.I)
SCHOLARLY_NAME = re.compile(r'\((?:Rastogi|Sanderson|Hanneder|Gnoli|Dyczkowski)\s+\d+')
SECTION_HEADING = re.compile(r'^(CHAPTER\s+\w+|The\s+[A-Z].*|“.*”)$')

results = {
    'verses': [],
    'sections': [],
    'footnotes': [],
    'sanskrit': [],
    'junk': [],
}

current_block = None

for i, line in enumerate(lines):
    s = line.strip()
    if not s:
        continue
    
    # Section heading?
    if re.match(r'^(CHAPTER\s+\w+)', s, re.I) or s in ['TANTRĀLOKA', 'The Introductory Verses', 'The Initial Invocation']:
        results['sections'].append((i, s))
        current_block = 'section'
        continue
    
    # Starts with apostrophe = footnote
    if s.startswith("'") or s.startswith('\u2018'):
        results['footnotes'].append((i, s))
        current_block = 'footnote'
        continue
    
    # Has a scholarly citation?
    if SCHOLARLY_NAME.search(s) or CITATION.search(s):
        results['footnotes'].append((i, s))
        current_block = 'footnote'
        continue
    
    # Manuscript reference?
    if MANUSCRIPT.search(s):
        results['footnotes'].append((i, s))
        current_block = 'footnote'
        continue
    
    # Sanskrit transliteration? (lowercase with diacritics, no uppercase English words)
    if len(s) > 30 and not re.search(r'[A-Z]{2,}', s) and re.search(r'[āīūṛṝḷḹśṣṅñṭḍṇ]', s) and not re.search(r'[A-Z][a-z]{2,}', s):
        results['sanskrit'].append((i, s))
        current_block = 'sanskrit'
        continue
    
    # Verse end marker?
    if VERSE_END.search(s):
        results['verses'].append((i, s))
        current_block = 'verse'
        continue
    
    # Page references?
    if PAGE_REF.search(s) and len(s) < 80:
        results['footnotes'].append((i, s))
        current_block = 'footnote'
        continue
    
    # Default: depends on context
    if current_block == 'footnote' or current_block == 'sanskrit':
        # Continuation of previous footnote or sanskrit
        if len(s) < 200:
            results[current_block].append((i, s))
        else:
            results['footnotes'].append((i, s))
    else:
        results['verses'].append((i, s))
        current_block = 'verse'

# Print results
print(f"Verses: {len(results['verses'])}")
print(f"Sections: {len(results['sections'])}")
print(f"Footnotes: {len(results['footnotes'])}")
print(f"Sanskrit: {len(results['sanskrit'])}")
print()

print("=== SECTIONS ===")
for i, s in results['sections'][:10]:
    print(f"  L{i}: {s}")

print("\n=== FIRST 20 VERSES ===")
for i, s in results['verses'][:20]:
    print(f"  L{i}: {s[:120]}")

print("\n=== FIRST 10 FOOTNOTES ===")
for i, s in results['footnotes'][:10]:
    print(f"  L{i}: {s[:120]}")

print("\n=== FIRST 5 SANSKRIT ===")
for i, s in results['sanskrit'][:5]:
    print(f"  L{i}: {s[:120]}")
