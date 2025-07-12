#!/usr/bin/env python3
import os
from pathlib import Path

def find_videos_needing_processing(root_path):
    """Find videos that need slide processing."""
    
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    
    videos_no_slides = []
    videos_generic_only = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        video_files = [f for f in filenames if not f.startswith('._') and 
                      any(f.lower().endswith(ext) for ext in video_extensions)]
        
        if not video_files:
            continue
        
        has_generic_slides = any(d.lower() in ['slides', 'slide'] for d in dirnames)
        
        for video_file in video_files:
            video_name_base = Path(video_file).stem
            
            # Check for video-specific slide folder
            has_specific = any(
                f"{video_name_base}_slides" == d or 
                f"{video_name_base}_slide" == d or
                (video_name_base.lower() in d.lower() and 'slide' in d.lower() 
                 and d.lower() not in ['slides', 'slide'])
                for d in dirnames
            )
            
            if not has_specific:
                video_info = {
                    'path': os.path.join(dirpath, video_file),
                    'filename': video_file,
                    'directory': dirpath
                }
                
                if has_generic_slides:
                    videos_generic_only.append(video_info)
                else:
                    videos_no_slides.append(video_info)
    
    return videos_no_slides, videos_generic_only

def main():
    root_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print("VIDEOS THAT NEED SLIDE PROCESSING")
    print("=" * 80)
    
    no_slides, generic_only = find_videos_needing_processing(root_path)
    
    if no_slides:
        print("\n1. VIDEOS WITH NO SLIDE FOLDERS (HIGH PRIORITY):")
        print("-" * 80)
        for i, video in enumerate(no_slides, 1):
            print(f"\n{i}. {video['filename']}")
            print(f"   Full path: {video['path']}")
    else:
        print("\n1. VIDEOS WITH NO SLIDE FOLDERS: None found")
    
    if generic_only:
        print(f"\n2. VIDEOS WITH ONLY GENERIC 'Slides' FOLDER ({len(generic_only)} videos):")
        print("   (These may benefit from video-specific slide capture)")
        print("-" * 80)
        for i, video in enumerate(generic_only, 1):
            print(f"\n{i}. {video['filename']}")
            print(f"   Full path: {video['path']}")
            print(f"   Current folder has generic 'Slides' folder")
    else:
        print("\n2. VIDEOS WITH ONLY GENERIC 'Slides' FOLDER: None found")
    
    # Summary
    total_need_processing = len(no_slides) + len(generic_only)
    print(f"\n{'=' * 80}")
    print(f"SUMMARY: {total_need_processing} videos may need slide processing")
    
    if generic_only:
        print("\nTo process these videos with batch capture, you can run:")
        print("python batch_slide_capture.py <video_path> --auto-select")

if __name__ == "__main__":
    main()