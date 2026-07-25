#!/usr/bin/env python3
"""
Clean Dyczkowski's Tantraloka text files for TTS-readability.
Strips OCR garbage, footnote markers, random punctuation.
Outputs per-volume clean .txt files.
"""
import re, os, shutil

INPUT_DIR = '/root/projects/tantraloka/texts'
OUTPUT_DIR = '/root/projects/tantraloka/texts-clean'
os.makedirs(OUTPUT_DIR, exist_ok=True)

files = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith('.txt'))

def clean_line(line):
    s = line.strip()
    if not s:
        return ''
    
    # Skip pure digit lines (page numbers)
    if s.isdigit():
        return ''
    
    # Remove form feeds
    s = s.replace('\x0c', '')
    
    # Remove OCR garbage: lines where >30% of chars are non-ASCII (Devanagari garbage)
    non_ascii = sum(1 for c in s if ord(c) > 127)
    if len(s) > 0 and non_ascii / len(s) > 0.3:
        return ''
    
    # Remove footnote reference markers like ⁷⁶³, ⁷⁰⁹, ¹²³ etc.
    s = re.sub(r'[\u2070-\u209f\u00b2\u00b3\u00b9\u2080-\u2089⁰¹²³⁴⁵⁶⁷⁸⁹ⁱⁿ]+', '', s)
    
    # Remove bracketed numbers like [123] but keep (250cd-251ab)
    s = re.sub(r'\[\d+\]', '', s)
    
    # Remove footnote markers like ⁷⁶³, ⁷⁸⁹ etc (these are superscript digits)
    s = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+', '', s)
    
    # Remove stray asterisks and excessive special chars
    s = re.sub(r'[\*\†\‡\§\¶]+', '', s)
    
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    
    # Remove lines that are just punctuation or symbols after cleaning
    if re.match(r'^[\s\-\—\|\/\\\.\,\;\:\!\?\'\"]+$', s):
        return ''
    
    return s

def clean_volume(filepath, output_path):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    
    lines = text.split('\n')
    cleaned = []
    prev_blank = False
    
    for line in lines:
        cl = clean_line(line)
        if cl == '':
            if not prev_blank:
                cleaned.append('')
                prev_blank = True
        else:
            cleaned.append(cl)
            prev_blank = False
    
    # Remove leading blank lines
    while cleaned and cleaned[0] == '':
        cleaned.pop(0)
    # Remove trailing blank lines  
    while cleaned and cleaned[-1] == '':
        cleaned.pop()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned))
    
    return len(cleaned)

stats = []
for fname in files:
    src = os.path.join(INPUT_DIR, fname)
    dst = os.path.join(OUTPUT_DIR, fname.replace('.txt', '_clean.txt'))
    nlines = clean_volume(src, dst)
    orig = sum(1 for _ in open(src))
    stats.append((fname, orig, nlines))

print(f"{'File':50s} {'Original':10s} {'Cleaned':10s}")
print('-' * 72)
for name, orig, clean in stats:
    vol = name.replace('tantraloka-', '').replace('-dyczkowski.txt', '').replace('.txt', '')
    print(f"{vol:50s} {orig:<10d} {clean:<10d}")

# Also output combined per-chapter as well?
print("\nCleaning complete. Output in texts-clean/")
