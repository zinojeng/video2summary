#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def find_videos_without_slides(root_path):
    """Find all video files that don't have corresponding slide folders."""
    
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    slide_folder_patterns = ['slides', 'slide', 'Slides', 'Slide']
    
    videos_without_slides = []
    total_videos = 0
    videos_with_slides = 0
    
    # Walk through directory tree
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Find video files in current directory
        video_files = []
        for filename in filenames:
            # Skip macOS hidden files
            if filename.startswith('._'):
                continue
                
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                video_files.append(filename)
                total_videos += 1
        
        if not video_files:
            continue
            
        # Check each video file
        for video_file in video_files:
            video_name_base = Path(video_file).stem
            has_slides = False
            
            # Check for slide folders in the same directory
            for dirname in dirnames:
                dirname_lower = dirname.lower()
                
                # Check if folder name contains slide patterns
                if any(pattern in dirname_lower for pattern in slide_folder_patterns):
                    has_slides = True
                    break
                    
                # Check if folder name contains video name + slide pattern
                if video_name_base.lower() in dirname_lower and any(pattern in dirname_lower for pattern in slide_folder_patterns):
                    has_slides = True
                    break
                    
                # Check for exact pattern: videoname_slides or videoname_slide
                if dirname.startswith(video_name_base) and any(dirname.endswith(f'_{pattern}') or dirname.endswith(f'_{pattern}s') for pattern in ['slide', 'Slide']):
                    has_slides = True
                    break
            
            if has_slides:
                videos_with_slides += 1
            else:
                videos_without_slides.append({
                    'path': os.path.join(dirpath, video_file),
                    'directory': dirpath,
                    'filename': video_file,
                    'folders_in_dir': dirnames
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
        
        for i, video_info in enumerate(videos_without_slides, 1):
            print(f"\n{i}. Video: {video_info['filename']}")
            print(f"   Full path: {video_info['path']}")
            print(f"   Directory: {video_info['directory']}")
            
            # Show folders in the same directory
            if video_info['folders_in_dir']:
                print(f"   Folders in directory: {', '.join(video_info['folders_in_dir'][:5])}")
                if len(video_info['folders_in_dir']) > 5:
                    print(f"                        ... and {len(video_info['folders_in_dir']) - 5} more")
            else:
                print("   No folders in this directory")
    else:
        print("\nAll videos have corresponding slide folders!")

if __name__ == "__main__":
    main()