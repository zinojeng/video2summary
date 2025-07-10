#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
示例：如何在代碼中使用改進模式
"""

from improved_slide_capture import capture_slides_improved

# 設置參數
video_path = "your_video.mp4"  # 替換為您的視頻路徑
output_folder = "output_slides"  # 輸出文件夾
threshold = 0.85  # 相似度閾值（0.7-0.95）

# 執行捕獲
print("開始使用改進模式捕獲幻燈片...")
success, result = capture_slides_improved(
    video_path=video_path,
    output_folder=output_folder,
    threshold=threshold
)

# 處理結果
if success:
    print(f"成功！捕獲了 {result['slide_count']} 張幻燈片")
    print(f"文件保存在: {result['output_folder']}")
else:
    print(f"失敗: {result.get('error', '未知錯誤')}")