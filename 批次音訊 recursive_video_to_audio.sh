#!/bin/bash

# Recursive Video to Audio Converter
# Usage: ./recursive_video_to_audio.sh [dircetory_path]
# Example: ./recursive_video_to_audio.sh /path/to/videos

set -u

# Default to current directory if no argument provided
SEARCH_DIR="${1:-.}"

# NOTE: This script does NOT require a Python virtual environment to run.
# It relies on the system-level 'ffmpeg' tool.
#
# Prerequisite: ffmpeg must be installed on your system.
# MacOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed. Please install it first."
    exit 1
fi

echo "Searching for video files in: $SEARCH_DIR"
echo "Target format: MP3"
echo "----------------------------------------"

# Counter
count=0

# Find and process video files
# Supported extensions: mp4, mkv, mov, avi, webm, flv, m4v, wmv
find "$SEARCH_DIR" -type f \( \
    -iname "*.mp4" -o \
    -iname "*.mkv" -o \
    -iname "*.mov" -o \
    -iname "*.avi" -o \
    -iname "*.webm" -o \
    -iname "*.flv" -o \
    -iname "*.m4v" -o \
    -iname "*.wmv" \
\) | while read -r video_file; do
    
    # Extract filename and extension
    dir_name=$(dirname "$video_file")
    base_name=$(basename "$video_file")
    file_name="${base_name%.*}"
    
    # Output file path (same directory)
    output_audio="$dir_name/$file_name.mp3"
    
    echo "Processing: $base_name"
    
    if [ -f "$output_audio" ]; then
        echo "  Skipping: Audio file already exists ($output_audio)"
    else
        # Convert video to audio
        # -vn: disable video
        # -acodec: audio codec (libmp3lame for mp3)
        # -q:a 2: variable bit rate quality (0-9, 2 is good/standard around 190kbps)
        # -y: overwrite output files without asking (we checked existence above, but just in case)
        # -loglevel error: reduce output noise
        
        ffmpeg -i "$video_file" -vn -acodec libmp3lame -q:a 2 -y "$output_audio" < /dev/null
        
        if [ $? -eq 0 ]; then
            echo "  Success: Converted to $file_name.mp3"
        else
            echo "  Error: Failed to convert $base_name"
        fi
    fi
    echo "----------------------------------------"
    
done

echo "Batch processing complete."
