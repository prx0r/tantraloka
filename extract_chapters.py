#!/usr/bin/env python3
"""
Split cleaned Tantraloka texts into per-āhnika (chapter) markdown files.
Also generate a TTS-friendly concatenated version.
"""
import re, os, json

CLEAN_DIR = '/root/projects/tantraloka/texts-clean'
OUTPUT_DIR = '/root/projects/tantraloka/texts-chapters'
TTS_DIR = '/root/projects/tantraloka/texts-tts'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

VOLUME_MAP = {
    1: 'Chapter 1',
    2: 'Chapter 2',
    3: 'Chapter 3',
    4: 'Chapter 4',
    5: 'Chapter 5',
    6: 'Chapter 6',
    7: 'Chapter 7',
    8: 'Chapter 8',
    9: 'Chapter 9',
    10: 'Chapter 10',
    11: 'Chapter 11',
}

# Map volume number to clean filename
def vol_to_file(v):
    if v <= 11:
        return f'tantraloka-vol{v}-dyczkowski_clean.txt'
    return None

chapter_ranges = {
    1: (1, 1), 2: (2, 3), 3: (4, 4), 4: (5, 6), 5: (7, 8),
    6: (9, 10), 7: (11, 14), 8: (15, 15), 9: (16, 27),
    10: (28, 29), 11: (30, 37)
}

# First pass: find all chapter headings in cleaned texts
chapter_breaks = {}  # vol -> list of (line_index, heading_text)

for vol in range(1, 12):
    fname = vol_to_file(vol)
    if not fname:
        continue
    fpath = os.path.join(CLEAN_DIR, fname)
    if not os.path.exists(fpath):
        print(f"Missing: {fpath}")
        continue
    
    with open(fpath) as f:
        lines = f.readlines()
    
    breaks = []
    for i, line in enumerate(lines):
        s = line.strip()
        # Match chapter headings
        if re.match(r'^CHAPTER\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|THIRTY|FORTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY|HUNDRED|\d+)', s, re.I):
            breaks.append((i, s))
        elif re.match(r'^Chapter\s+\d+', s):
            breaks.append((i, s))
    
    chapter_breaks[vol] = breaks
    print(f"Volume {vol}: {len(breaks)} chapter breaks found")

# Split and save per chapter
# For volumes with multiple chapters, split at chapter breaks
for vol in range(1, 12):
    fname = vol_to_file(vol)
    fpath = os.path.join(CLEAN_DIR, fname)
    if not os.path.exists(fpath):
        continue
    
    with open(fpath) as f:
        lines = f.readlines()
    
    breaks = chapter_breaks.get(vol, [])
    
    if len(breaks) <= 1:
        # Single chapter volume — just copy
        ch_num = chapter_ranges[vol][0]
        out = os.path.join(OUTPUT_DIR, f'ahnika-{ch_num:02d}.md')
        with open(out, 'w') as f:
            f.write(f"# Āhnika {ch_num}\n\n")
            f.writelines(lines)
        print(f"  -> Āhnika {ch_num}: {len(lines)} lines")
    else:
        # Multi-chapter volume — split at breaks
        chapters_in_vol = list(range(chapter_ranges[vol][0], chapter_ranges[vol][1] + 1))
        for idx, ch_num in enumerate(chapters_in_vol):
            start = breaks[idx][0] if idx < len(breaks) else 0
            end = breaks[idx + 1][0] if idx + 1 < len(breaks) else len(lines)
            out = os.path.join(OUTPUT_DIR, f'ahnika-{ch_num:02d}.md')
            with open(out, 'w') as f:
                f.write(f"# Āhnika {ch_num}\n\n")
                f.writelines(lines[start:end])
            print(f"  -> Āhnika {ch_num}: lines {start}-{end}")

# Generate TTS-friendly concatenated files
# One file per āhnika, cleaned for speech
print("\nGenerating TTS files...")
for ch in range(1, 38):
    src = os.path.join(OUTPUT_DIR, f'ahnika-{ch:02d}.md')
    if not os.path.exists(src):
        print(f"  Missing: Āhnika {ch}")
        continue
    
    with open(src) as f:
        text = f.read()
    
    # Clean for TTS: remove markdown headers, excessive whitespace
    text = re.sub(r'^#.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    dst = os.path.join(TTS_DIR, f'ahnika-{ch:02d}.txt')
    with open(dst, 'w') as f:
        f.write(text)
    word_count = len(text.split())
    print(f"  Āhnika {ch}: {word_count} words")

# Also create a full combined file
print("\nGenerating full combined TTS text...")
all_text = []
for ch in range(1, 38):
    src = os.path.join(TTS_DIR, f'ahnika-{ch:02d}.txt')
    if os.path.exists(src):
        with open(src) as f:
            all_text.append(f"=== Āhnika {ch} ===\n\n{f.read()}")
        
with open(os.path.join(TTS_DIR, 'tantraloka-complete.txt'), 'w') as f:
    f.write('\n\n'.join(all_text))

total_words = sum(len(t.split()) for t in all_text)
print(f"Total: {total_words} words across 37 āhnikas")

# Generate index/table of contents
toc = []
for ch in range(1, 38):
    src = os.path.join(OUTPUT_DIR, f'ahnika-{ch:02d}.md')
    if os.path.exists(src):
        with open(src) as f:
            # Find first heading as title
            first_line = f.readline().strip().replace('# ', '')
            toc.append({"ahnika": ch, "file": f"ahnika-{ch:02d}.md", "title": first_line})

with open(os.path.join(OUTPUT_DIR, 'toc.json'), 'w') as f:
    json.dump(toc, f, indent=2)

print(f"\nTable of contents written to toc.json")
print("Done.")
