#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path

# Load progress
with open('batch_progress_openai.json', 'r') as f:
    progress = json.load(f)

# Find all folders
all_folders = []
base_path = '/Volumes/WD_BLACK/國際年會/ADA2025'
for folder in Path(base_path).rglob('*_slides'):
    if folder.name != 'selected_slides' and folder.is_dir():
        all_folders.append(str(folder))

print(f"Total folders: {len(all_folders)}")
print(f"Processed: {len(progress['processed'])}")
print(f"Failed: {len(progress['failed'])}")
print()

# Check which ones need processing
need_process = []
for folder in sorted(all_folders):
    if folder not in progress['processed'] and folder not in progress['failed']:
        # Check if has selected_slides
        if os.path.exists(os.path.join(folder, 'selected_slides')):
            # Check if already has OpenAI analysis
            if not os.path.exists(os.path.join(folder, 'selected_slides_analysis.md')):
                need_process.append(folder)
                print(f'Needs processing: {os.path.basename(os.path.dirname(folder))}/{os.path.basename(folder)}')

print(f"\nTotal folders needing processing: {len(need_process)}")