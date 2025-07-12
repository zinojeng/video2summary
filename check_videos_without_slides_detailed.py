#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def find_videos_without_slides(root_path):
    """Find all video files that don't have corresponding slide folders."""
    
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    
    videos_without_slides = []
    total_videos = 0
    videos_with_slides = 0
    
    # Walk through directory tree
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Find video files in current directory
        for filename in filenames:
            # Skip macOS hidden files
            if filename.startswith('._'):
                continue
                
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                total_videos += 1
                video_path = os.path.join(dirpath, filename)
                video_name_base = Path(filename).stem
                
                # Check for corresponding slide folder
                has_slides = False
                slide_folders_found = []
                
                # Look for slide folders in the same directory
                for dirname in dirnames:
                    dirname_lower = dirname.lower()
                    video_name_lower = video_name_base.lower()
                    
                    # Check various patterns for slide folders
                    is_slide_folder = False
                    
                    # Pattern 1: exact match with _slides or _slide suffix
                    if dirname == f"{video_name_base}_slides" or dirname == f"{video_name_base}_slide":
                        is_slide_folder = True
                    # Pattern 2: just "Slides" or "slides" folder
                    elif dirname.lower() in ['slides', 'slide']:
                        is_slide_folder = True
                    # Pattern 3: contains video name and slide keyword
                    elif video_name_lower in dirname_lower and ('slide' in dirname_lower):
                        is_slide_folder = True
                    
                    if is_slide_folder:
                        has_slides = True
                        slide_folders_found.append(dirname)
                
                if has_slides:
                    videos_with_slides += 1
                else:
                    # Get all folders in directory for context
                    all_folders = [d for d in dirnames if not d.startswith('.')]
                    videos_without_slides.append({
                        'path': video_path,
                        'directory': dirpath,
                        'filename': filename,
                        'video_base_name': video_name_base,
                        'folders_in_dir': all_folders,
                        'slide_folders_found': slide_folders_found
                    })
    
    return videos_without_slides, total_videos, videos_with_slides

def main():
    root_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print(f"Searching for videos without slide folders in: {root_path}")
    print("=" * 80)
    
    videos_without_slides, total_videos, videos_with_slides = find_videos_without_slides(root_path)
    
    print(f"\nTotal videos found: {total_videos}")
    print(f"Videos with slide folders: {videos_with_slides}")
    print(f"Videos WITHOUT slide folders: {len(videos_without_slides)}")
    print("\n" + "=" * 80)
    
    if videos_without_slides:
        print("\nVIDEOS WITHOUT SLIDE FOLDERS:")
        print("=" * 80)
        
        # Group by directory for better readability
        grouped = {}
        for video_info in videos_without_slides:
            dir_path = video_info['directory']
            if dir_path not in grouped:
                grouped[dir_path] = []
            grouped[dir_path].append(video_info)
        
        for dir_path, videos in grouped.items():
            print(f"\nDirectory: {dir_path}")
            print("-" * 80)
            
            for video_info in videos:
                print(f"  Video: {video_info['filename']}")
                print(f"  Expected slide folder: {video_info['video_base_name']}_slides")
                
                if video_info['folders_in_dir']:
                    print(f"  Existing folders: {', '.join(video_info['folders_in_dir'][:3])}")
                    if len(video_info['folders_in_dir']) > 3:
                        print(f"                   ... and {len(video_info['folders_in_dir']) - 3} more")
                else:
                    print("  No folders in this directory")
                print()
    else:
        print("\nAll videos have corresponding slide folders!")

if __name__ == "__main__":
    main()