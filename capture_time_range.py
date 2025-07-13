#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Capture slides from a specific time range with custom threshold
"""

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import os
import sys

def capture_time_range(video_path, output_folder, start_time, end_time, threshold=0.5, step_seconds=5):
    """Capture slides from specific time range"""
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Convert time to frames
    start_frame = int(start_time * fps)
    end_frame = min(int(end_time * fps), total_frames)
    step_frames = int(step_seconds * fps)
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Capturing from {start_time}s to {end_time}s")
    print(f"Frame range: {start_frame} to {end_frame}")
    print(f"Step: {step_seconds}s ({step_frames} frames)")
    print(f"Threshold: {threshold}")
    
    slides = []
    prev_frame = None
    
    # Jump to start
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    frame_idx = start_frame
    count = 0
    
    while frame_idx < end_frame:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            break
            
        # Convert to grayscale for comparison
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # First frame or significant change
        if prev_frame is None:
            is_new_slide = True
        else:
            # Calculate similarity
            similarity = ssim(prev_frame, gray)
            is_new_slide = similarity < threshold
            
        if is_new_slide:
            timestamp = frame_idx / fps
            filename = f"speaker1_slide_{count:03d}_t{timestamp:.1f}s.jpg"
            filepath = os.path.join(output_folder, filename)
            cv2.imwrite(filepath, frame)
            print(f"Captured: {filename} (similarity: {similarity if prev_frame is not None else 'N/A'})")
            slides.append((timestamp, filename))
            count += 1
            prev_frame = gray
            
        # Progress
        if frame_idx % (step_frames * 10) == 0:
            progress = (frame_idx - start_frame) / (end_frame - start_frame) * 100
            print(f"Progress: {progress:.1f}%")
            
        frame_idx += step_frames
    
    cap.release()
    print(f"\nCaptured {count} slides")
    return slides

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python capture_time_range.py <video> <output_folder> <start_seconds> <end_seconds> [threshold]")
        sys.exit(1)
        
    video_path = sys.argv[1]
    output_folder = sys.argv[2]
    start_time = float(sys.argv[3])
    end_time = float(sys.argv[4])
    threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
    
    capture_time_range(video_path, output_folder, start_time, end_time, threshold)