#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
捕獲特定時間段的幻燈片和動畫
"""

import cv2
import numpy as np
import os
from typing import List, Tuple


def capture_time_range(video_path: str, start_time: float, end_time: float, output_folder: str):
    """
    捕獲指定時間段的幻燈片變化
    
    參數:
        video_path: 視頻路徑
        start_time: 開始時間（秒）
        end_time: 結束時間（秒）
        output_folder: 輸出文件夾
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # 計算幀範圍
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    
    print(f"處理時間段: {start_time}秒 - {end_time}秒")
    print(f"幀範圍: {start_frame} - {end_frame}")
    print(f"FPS: {fps}")
    
    os.makedirs(output_folder, exist_ok=True)
    
    # 跳到開始位置
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    frames_captured = []
    prev_frame = None
    frame_count = 0
    
    # 逐幀處理
    for frame_idx in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_idx / fps
        
        # 每秒至少檢查2次
        if frame_idx % max(1, int(fps / 2)) == 0:
            if prev_frame is None:
                # 第一幀
                frames_captured.append((frame_idx, frame.copy(), current_time))
                prev_frame = frame
                print(f"捕獲第一幀: t={current_time:.2f}s")
            else:
                # 計算變化
                gray1 = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 計算差異
                diff = cv2.absdiff(gray1, gray2)
                mean_diff = np.mean(diff)
                
                # 計算結構相似性（更精確）
                score = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)[0][0]
                
                # 如果有變化（使用較低的閾值來捕獲細微變化）
                if mean_diff > 5 or score < 0.98:
                    frames_captured.append((frame_idx, frame.copy(), current_time))
                    prev_frame = frame
                    print(f"檢測到變化: t={current_time:.2f}s, 差異={mean_diff:.1f}, 相似度={score:.3f}")
        
        frame_count += 1
        
        # 顯示進度
        if frame_count % 30 == 0:
            progress = (frame_idx - start_frame) / (end_frame - start_frame) * 100
            print(f"進度: {progress:.1f}%")
    
    cap.release()
    
    # 保存捕獲的幀
    print(f"\n保存 {len(frames_captured)} 張圖片...")
    saved_files = []
    
    # 分組保存（如果時間接近的認為是同一張幻燈片的動畫）
    slide_groups = []
    current_group = []
    
    for i, (frame_idx, frame, timestamp) in enumerate(frames_captured):
        if i == 0:
            current_group.append((frame_idx, frame, timestamp))
        else:
            # 如果與前一幀時間差小於5秒，認為是同一組
            prev_timestamp = frames_captured[i-1][2]
            if timestamp - prev_timestamp < 5.0:
                current_group.append((frame_idx, frame, timestamp))
            else:
                if current_group:
                    slide_groups.append(current_group)
                current_group = [(frame_idx, frame, timestamp)]
    
    if current_group:
        slide_groups.append(current_group)
    
    # 保存分組後的圖片
    for group_idx, group in enumerate(slide_groups):
        slide_num = group_idx + 1
        
        if len(group) == 1:
            # 單張幻燈片
            _, frame, timestamp = group[0]
            filename = f"slide_{slide_num:03d}_t{timestamp:.1f}s.jpg"
            filepath = os.path.join(output_folder, filename)
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_files.append(filepath)
            print(f"保存: {filename}")
        else:
            # 動畫序列
            print(f"幻燈片 {slide_num} 有 {len(group)} 個狀態:")
            for sub_idx, (_, frame, timestamp) in enumerate(group):
                filename = f"slide_{slide_num:03d}_{sub_idx+1}_t{timestamp:.1f}s.jpg"
                filepath = os.path.join(output_folder, filename)
                cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_files.append(filepath)
                print(f"  {filename}")
    
    return saved_files


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python capture_specific_time.py <視頻文件> [開始時間] [結束時間]")
        print("示例: python capture_specific_time.py video.mp4 190 210")
        print("(默認處理 3:10 到 3:30)")
        sys.exit(1)
    
    video_file = sys.argv[1]
    start = float(sys.argv[2]) if len(sys.argv) > 2 else 190  # 3:10
    end = float(sys.argv[3]) if len(sys.argv) > 3 else 210    # 3:30
    
    output_dir = f"time_capture_{int(start)}_{int(end)}"
    
    print(f"捕獲視頻片段: {start}秒 ({int(start)//60}:{start%60:02.0f}) - {end}秒 ({int(end)//60}:{end%60:02.0f})")
    print("=" * 60)
    
    files = capture_time_range(video_file, start, end, output_dir)
    
    print(f"\n完成！保存了 {len(files)} 張圖片到 {output_dir}")
    
    # 分析結果
    animation_count = 0
    for f in files:
        if "_" in os.path.basename(f).split("_t")[0].split("_", 2)[-1]:
            animation_count += 1
    
    if animation_count > 0:
        print(f"其中包含 {animation_count} 張動畫狀態圖片")