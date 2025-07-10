#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
示範如何使用改進模式捕獲幻燈片
"""

import sys
import os
from improved_slide_capture import capture_slides_improved

def main():
    # 檢查命令行參數
    if len(sys.argv) < 2:
        print("使用方法: python run_improved_mode.py <視頻文件路徑>")
        print("\n示例:")
        print("  python run_improved_mode.py ~/Desktop/presentation.mp4")
        print("  python run_improved_mode.py /path/to/your/video.mp4")
        return
    
    # 獲取視頻文件路徑
    video_path = sys.argv[1]
    
    # 檢查文件是否存在
    if not os.path.exists(video_path):
        print(f"錯誤：找不到視頻文件 {video_path}")
        return
    
    # 設置輸出文件夾
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_folder = f"slides_improved_{video_name}"
    
    # 設置相似度閾值（可選，預設為 0.85）
    threshold = 0.85
    
    print("=" * 60)
    print("使用改進模式捕獲幻燈片")
    print("=" * 60)
    print(f"視頻文件: {video_path}")
    print(f"輸出文件夾: {output_folder}")
    print(f"相似度閾值: {threshold}")
    print("=" * 60)
    
    # 調用改進的捕獲函數
    success, result = capture_slides_improved(video_path, output_folder, threshold)
    
    if success:
        print("\n✅ 捕獲成功！")
        print(f"📊 統計信息:")
        print(f"  - 總幀數: {result.get('total_frames', 'N/A')}")
        print(f"  - 捕獲幻燈片數: {result['slide_count']}")
        print(f"  - 輸出位置: {result['output_folder']}")
        
        # 列出保存的文件
        if 'saved_files' in result and result['saved_files']:
            print(f"\n📁 保存的文件 (前5個):")
            for i, file_path in enumerate(result['saved_files'][:5]):
                print(f"  {i+1}. {os.path.basename(file_path)}")
            if len(result['saved_files']) > 5:
                print(f"  ... 還有 {len(result['saved_files']) - 5} 個文件")
    else:
        print(f"\n❌ 捕獲失敗: {result.get('error', '未知錯誤')}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()