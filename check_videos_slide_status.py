#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def analyze_slide_folders(root_path):
    """Analyze video files and their slide folder status."""
    
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    
    videos_no_slides = []  # No slide folders at all
    videos_generic_slides = []  # Only have generic "Slides" folder
    videos_specific_slides = []  # Have video-specific slide folders
    total_videos = 0
    
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
        
        # Analyze slide folders in this directory
        has_generic_slides = any(d.lower() in ['slides', 'slide'] for d in dirnames)
        
        # Check each video
        for video_file in video_files:
            video_path = os.path.join(dirpath, video_file)
            video_name_base = Path(video_file).stem
            
            # Look for video-specific slide folder
            has_specific_slides = False
            specific_slide_folders = []
            
            for dirname in dirnames:
                # Check if folder is specific to this video
                if (f"{video_name_base}_slides" == dirname or 
                    f"{video_name_base}_slide" == dirname or
                    (video_name_base.lower() in dirname.lower() and 'slide' in dirname.lower() and dirname.lower() not in ['slides', 'slide'])):
                    has_specific_slides = True
                    specific_slide_folders.append(dirname)
            
            # Categorize the video
            if has_specific_slides:
                videos_specific_slides.append({
                    'path': video_path,
                    'directory': dirpath,
                    'filename': video_file,
                    'slide_folders': specific_slide_folders
                })
            elif has_generic_slides:
                videos_generic_slides.append({
                    'path': video_path,
                    'directory': dirpath,
                    'filename': video_file
                })
            else:
                videos_no_slides.append({
                    'path': video_path,
                    'directory': dirpath,
                    'filename': video_file,
                    'all_folders': [d for d in dirnames if not d.startswith('.')]
                })
    
    return videos_no_slides, videos_generic_slides, videos_specific_slides, total_videos

def main():
    root_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print(f"Analyzing slide folder status in: {root_path}")
    print("=" * 80)
    
    no_slides, generic_slides, specific_slides, total = analyze_slide_folders(root_path)
    
    print(f"\nTotal videos found: {total}")
    print(f"Videos with specific slide folders: {len(specific_slides)}")
    print(f"Videos with only generic 'Slides' folder: {len(generic_slides)}")
    print(f"Videos with NO slide folders: {len(no_slides)}")
    print("\n" + "=" * 80)
    
    # Show videos without any slides
    if no_slides:
        print("\nVIDEOS WITH NO SLIDE FOLDERS AT ALL:")
        print("=" * 80)
        for video in no_slides:
            print(f"\nVideo: {video['filename']}")
            print(f"Path: {video['path']}")
            print(f"Directory: {video['directory']}")
            if video['all_folders']:
                print(f"Folders in directory: {', '.join(video['all_folders'][:3])}")
            else:
                print("No folders in directory")
    
    # Show videos with only generic slides
    if generic_slides:
        print("\n\nVIDEOS WITH ONLY GENERIC 'Slides' FOLDER:")
        print("(These might benefit from video-specific slide capture)")
        print("=" * 80)
        
        # Group by directory
        grouped = {}
        for video in generic_slides:
            dir_path = video['directory']
            if dir_path not in grouped:
                grouped[dir_path] = []
            grouped[dir_path].append(video)
        
        for dir_path, videos in grouped.items():
            print(f"\nDirectory: {dir_path}")
            for video in videos:
                print(f"  - {video['filename']}")
    
    # Summary of videos with specific slides
    if specific_slides:
        print(f"\n\nVIDEOS WITH SPECIFIC SLIDE FOLDERS: {len(specific_slides)} videos")
        print("These videos already have dedicated slide folders.")

if __name__ == "__main__":
    main()