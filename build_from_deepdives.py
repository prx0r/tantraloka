#!/usr/bin/env python3
"""
Build clean reading text from deepdive files.
Each deepdive has Dyczkowski translations already cleanly extracted.
"""
import re, os, glob

DEEPDIVE_DIR = '/root/projects/tantraloka/video-plans/deepdive'
OUTPUT_DIR = '/root/projects/tantraloka/read-clean'
os.makedirs(OUTPUT_DIR, exist_ok=True)

files = sorted(glob.glob(os.path.join(DEEPDIVE_DIR, '*.md')))

all_text = []
current_ahnika = 0

for fpath in files:
    fname = os.path.basename(fpath)
    
    with open(fpath) as f:
        content = f.read()
    
    # Extract title
    title = ''
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line.replace('# ', '').strip()
            break
    
    # Extract Dyczkowski translations - look for "**Dyczkowski Translation:**" blocks
    # These contain the clean verse translations
    translations = []
    in_translation = False
    current_translation = ''
    
    for line in content.split('\n'):
        if '**Dyczkowski Translation:**' in line:
            if current_translation:
                translations.append(current_translation.strip())
            in_translation = True
            # Get the text after the bold marker
            after = line.split('**Dyczkowski Translation:**')[-1].strip()
            if after:
                current_translation = after
            else:
                current_translation = ''
        elif in_translation:
            if line.startswith('**') or line.startswith('---') or line.startswith('###'):
                if current_translation:
                    translations.append(current_translation.strip())
                current_translation = ''
                in_translation = False
            else:
                # Skip empty continuation lines
                stripped = line.strip()
                if stripped and not stripped.startswith('*'):
                    current_translation += ' ' + stripped
    
    if current_translation:
        translations.append(current_translation.strip())
    
    if translations:
        all_text.append(f"\n## {title}\n")
        for t in translations:
            # Clean up the translation
            t = re.sub(r'\*+', '', t)  # Remove bold markers
            t = re.sub(r'\s+', ' ', t).strip()
            # Remove leading/trailing quotes
            t = t.strip('"\'"""')
            all_text.append(f"\n{t}\n")

# Write combined
output = '\n'.join(all_text)
outpath = os.path.join(OUTPUT_DIR, 'tantraloka-verses.txt')
with open(outpath, 'w') as f:
    f.write(output)

words = len(output.split())
print(f"Extracted translations from {len(files)} deepdive files")
print(f"Total: {words} words")
print(f"Written to: {outpath}")
print(f"\nFirst 2000 chars:")
print(output[:2000])
