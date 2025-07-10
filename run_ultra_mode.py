#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
運行超級模式 - 專門檢測動畫效果
"""

import sys
import os
from ultra_slide_capture import capture_slides_ultra

def main():
    if len(sys.argv) < 2:
        print("使用方法: python run_ultra_mode.py <視頻文件路徑>")
        return
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"錯誤：找不到視頻文件 {video_path}")
        return
    
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_folder = f"slides_ultra_{video_name}"
    
    print("=" * 60)
    print("🚀 超級模式 - 動畫效果檢測")
    print("=" * 60)
    print(f"視頻: {os.path.basename(video_path)}")
    print(f"輸出: {output_folder}")
    print("特色: 檢測同一幻燈片的不同動畫狀態")
    print("=" * 60)
    
    success, result = capture_slides_ultra(video_path, output_folder, threshold=0.85)
    
    if success:
        print("\n✅ 捕獲成功！")
        print(f"📊 統計:")
        print(f"  - 幻燈片組數: {result.get('slide_groups', 'N/A')}")
        print(f"  - 總圖片數: {result['slide_count']} (含動畫狀態)")
        print(f"  - 輸出位置: {result['output_folder']}")
        
        # 分析動畫序列
        if 'saved_files' in result:
            animation_count = 0
            current_slide = None
            
            for file_path in result['saved_files']:
                filename = os.path.basename(file_path)
                # 檢查是否為動畫序列 (slide_XXX_Y 格式)
                if '_' in filename.split('_t')[0]:
                    parts = filename.split('_')
                    if len(parts) >= 3:
                        slide_num = parts[1]
                        if slide_num != current_slide:
                            current_slide = slide_num
                            animation_count += 1
            
            if animation_count > 0:
                print(f"\n🎬 檢測到 {animation_count} 組動畫序列")
    else:
        print(f"\n❌ 捕獲失敗: {result.get('error', '未知錯誤')}")

if __name__ == "__main__":
    main()