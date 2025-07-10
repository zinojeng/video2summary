#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
動畫檢測演示 - 只處理視頻的一部分
"""

import sys
import os
from fast_animation_capture import FastAnimationCapture
import cv2


def demo_capture(video_path: str, duration_minutes: int = 10):
    """演示動畫捕獲（只處理前N分鐘）"""
    
    # 打開視頻獲取信息
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    # 計算要處理的幀數
    max_frames = int(fps * 60 * duration_minutes)
    frames_to_process = min(max_frames, total_frames)
    
    print(f"視頻信息:")
    print(f"- 總時長: {total_frames/fps/60:.1f} 分鐘")
    print(f"- 演示處理: 前 {duration_minutes} 分鐘")
    print(f"- 處理幀數: {frames_to_process} / {total_frames}")
    print("=" * 60)
    
    # 創建輸出文件夾
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_folder = f"demo_animation_{video_name}"
    
    # 創建捕獲器並修改總幀數
    capturer = FastAnimationCapture(video_path, output_folder)
    capturer.total_frames = frames_to_process  # 只處理前N分鐘
    
    # 執行捕獲
    success, result = capturer.fast_capture()
    
    if success:
        print("\n✅ 演示完成！")
        print(f"在前 {duration_minutes} 分鐘內：")
        print(f"- 主幻燈片: {result.get('main_slides', 0)} 張")
        print(f"- 總圖片數: {result['slide_count']} 張（含動畫）")
        print(f"- 輸出位置: {result['output_folder']}")
        
        # 顯示一些例子
        if 'saved_files' in result and len(result['saved_files']) > 0:
            print("\n📸 捕獲示例:")
            for i, file_path in enumerate(result['saved_files'][:10]):
                filename = os.path.basename(file_path)
                print(f"  {filename}")
            
            if len(result['saved_files']) > 10:
                print(f"  ... 還有 {len(result['saved_files']) - 10} 張")
    else:
        print(f"\n❌ 失敗: {result.get('error', '未知錯誤')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python demo_animation_capture.py <視頻文件路徑> [處理分鐘數]")
        print("示例: python demo_animation_capture.py video.mp4 5")
        sys.exit(1)
    
    video_file = sys.argv[1]
    minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    demo_capture(video_file, minutes)