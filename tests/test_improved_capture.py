#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試改進的幻燈片捕獲功能
比較標準模式和改進模式的性能
"""

import os
import sys
import time
from video_audio_processor import capture_slides_from_video
from improved_slide_capture import capture_slides_improved


def test_capture_methods(video_path: str):
    """測試並比較兩種捕獲方法"""
    
    if not os.path.exists(video_path):
        print(f"錯誤：找不到視頻文件 {video_path}")
        return
    
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # 測試標準方法
    print("=" * 60)
    print("測試標準捕獲方法...")
    print("=" * 60)
    
    output_folder_standard = f"slides_standard_{base_name}"
    start_time = time.time()
    
    success, result = capture_slides_from_video(
        video_path, output_folder_standard, similarity_threshold=0.85
    )
    
    standard_time = time.time() - start_time
    
    if success:
        standard_count = result.get("slide_count", 0)
        print(f"\n標準方法結果：")
        print(f"- 捕獲幻燈片數：{standard_count}")
        print(f"- 處理時間：{standard_time:.2f} 秒")
        print(f"- 輸出文件夾：{output_folder_standard}")
    else:
        print(f"標準方法失敗：{result}")
        return
    
    # 測試改進方法
    print("\n" + "=" * 60)
    print("測試改進捕獲方法...")
    print("=" * 60)
    
    output_folder_improved = f"slides_improved_{base_name}"
    start_time = time.time()
    
    success, result = capture_slides_improved(
        video_path, output_folder_improved, threshold=0.85
    )
    
    improved_time = time.time() - start_time
    
    if success:
        improved_count = result.get("slide_count", 0)
        print(f"\n改進方法結果：")
        print(f"- 捕獲幻燈片數：{improved_count}")
        print(f"- 處理時間：{improved_time:.2f} 秒")
        print(f"- 輸出文件夾：{output_folder_improved}")
    else:
        print(f"改進方法失敗：{result}")
        return
    
    # 比較結果
    print("\n" + "=" * 60)
    print("性能比較：")
    print("=" * 60)
    
    speed_improvement = (standard_time / improved_time) if improved_time > 0 else 0
    print(f"速度提升：{speed_improvement:.2f}x")
    print(f"時間節省：{standard_time - improved_time:.2f} 秒")
    
    if standard_count != improved_count:
        diff = improved_count - standard_count
        if diff > 0:
            print(f"改進方法多捕獲了 {diff} 張幻燈片（可能檢測到了之前遺漏的）")
        else:
            print(f"改進方法少捕獲了 {-diff} 張幻燈片（可能去除了重複的）")
    else:
        print("兩種方法捕獲的幻燈片數量相同")
    
    print("\n提示：可以手動檢查兩個輸出文件夾，比較捕獲結果的質量")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python test_improved_capture.py <視頻文件路徑>")
        sys.exit(1)
    
    video_file = sys.argv[1]
    test_capture_methods(video_file)