#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
繼續批次處理剩餘的轉錄文件
"""

import os
import sys
import json
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("用法: python continue_transcription_notes.py <base_path> <gemini_api_key>")
        sys.exit(1)
    
    base_path = sys.argv[1]
    api_key = sys.argv[2]
    
    # 載入進度
    progress_file = 'transcription_notes_progress_v2.json'
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        print(f"\n✅ 已處理: {len(progress['processed'])} 個文件")
        print(f"❌ 失敗: {len(progress['failed'])} 個文件")
        print(f"💰 已使用 Token: {progress['stats'].get('total_tokens', 0):,}")
    else:
        print("找不到進度文件")
        return
    
    # 查找所有 SRT 文件
    srt_files = list(Path(base_path).rglob('transcription*.srt'))
    srt_files = [f for f in srt_files if not f.name.startswith('._')]
    
    # 統計剩餘的文件
    remaining = []
    for srt_file in srt_files:
        # 檢查對應的 txt 文件是否已處理
        txt_file = srt_file.with_suffix('.txt')
        if str(txt_file) not in progress['processed'] and str(srt_file) not in progress['processed']:
            remaining.append(str(srt_file))
    
    print(f"\n📊 統計：")
    print(f"  總共找到 SRT 文件: {len(srt_files)} 個")
    print(f"  剩餘待處理: {len(remaining)} 個")
    
    if remaining:
        print(f"\n剩餘的文件：")
        for i, file_path in enumerate(remaining[:10], 1):
            print(f"  {i}. {os.path.basename(os.path.dirname(file_path))}/{os.path.basename(file_path)}")
        if len(remaining) > 10:
            print(f"  ... 還有 {len(remaining) - 10} 個文件")
    
    # 確認是否繼續
    if remaining:
        print(f"\n準備繼續處理 {len(remaining)} 個文件")
        confirm = input("是否繼續？(y/n): ")
        if confirm.lower() == 'y':
            # 執行批次處理
            import subprocess
            cmd = ['python', 'batch_transcription_notes_v2.py', base_path, api_key]
            subprocess.run(cmd)
    else:
        print("\n✅ 所有文件都已處理完成！")

if __name__ == "__main__":
    main()