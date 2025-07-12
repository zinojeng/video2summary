#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
處理剩餘的 txt 轉錄文件
"""

import os
import sys
from pathlib import Path

# 剩餘的文件列表
remaining_files = [
    "/Volumes/WD_BLACK/國際年會/ADA2025/Unraveling the Secrets of Energy, Appetite, and Sugar Control /transcription-31.txt",
    "/Volumes/WD_BLACK/國際年會/ADA2025/Screening and Primary Prevention Strategies for ASCVD in Diabetes/transcription-27.txt",
    "/Volumes/WD_BLACK/國際年會/ADA2025/Opening a Door to Precision Medicine—Lessons from Human Kidney Tissue in Diabetes/transcription-25.txt",
    "/Volumes/WD_BLACK/國際年會/ADA2025/Ready for Prime Time?—Pharmacoepidemiology and Real-World Evidence /transcription-26.txt",
    "/Volumes/WD_BLACK/國際年會/ADA2025/Timing Is Everything—Circadian Rhythms in Health and Disease /transcription-30.txt"
]

def main():
    if len(sys.argv) < 2:
        print("用法: python process_remaining_txt.py <gemini_api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    print(f"\n📝 準備處理 {len(remaining_files)} 個剩餘的 txt 文件")
    
    # 檢查文件是否存在
    existing_files = []
    for file_path in remaining_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
            print(f"✓ {os.path.basename(os.path.dirname(file_path))}")
        else:
            print(f"✗ 文件不存在: {file_path}")
    
    if existing_files:
        print(f"\n找到 {len(existing_files)} 個文件，開始處理...")
        
        # 創建臨時文件列表
        temp_file = "temp_remaining_files.txt"
        with open(temp_file, 'w') as f:
            for file_path in existing_files:
                f.write(file_path + '\n')
        
        # 運行批次處理
        import subprocess
        cmd = ['python', 'batch_transcription_notes_v2.py', 
               '/Volumes/WD_BLACK/國際年會/ADA2025', api_key]
        subprocess.run(cmd)
        
        # 刪除臨時文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
    else:
        print("\n❌ 沒有找到任何文件")

if __name__ == "__main__":
    main()