#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
轉錄筆記處理最終總結
"""

import os
import json
from pathlib import Path
from datetime import datetime


def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print("\n📊 ADA2025 轉錄筆記處理最終總結")
    print("="*80)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 載入進度
    progress_file = 'transcription_notes_progress_v2.json'
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    
    # 查找生成的筆記文件（排除隱藏文件）
    notes_files = []
    for f in Path(base_path).rglob('*_detailed_notes.md'):
        if not f.name.startswith('._'):
            notes_files.append(f)
    
    # 統計
    print("\n✅ 處理完成總結：")
    print(f"  • 成功處理轉錄文件: {len(progress['processed'])} 個")
    print(f"  • 生成詳細演講筆記: {len(notes_files)} 個")
    print(f"  • 使用 Gemini 2.5 Pro tokens: {progress['stats'].get('total_tokens', 0):,}")
    
    # 成本估算
    total_tokens = progress['stats'].get('total_tokens', 0)
    estimated_cost = (total_tokens / 1_000_000) * 7.5
    print(f"  • 估計成本: ${estimated_cost:.2f} USD")
    
    # 文件類型
    txt_count = sum(1 for f in progress['processed'] if f.endswith('.txt'))
    srt_count = sum(1 for f in progress['processed'] if f.endswith('.srt'))
    print(f"\n📄 文件類型：")
    print(f"  • TXT 轉錄: {txt_count} 個")
    print(f"  • SRT 字幕: {srt_count} 個")
    
    # 列出處理的會議
    print(f"\n📁 已處理的會議（{len(notes_files)} 場）：")
    folders = sorted(set(f.parent.name for f in notes_files))
    for i, folder in enumerate(folders, 1):
        print(f"  {i:2d}. {folder}")
    
    print("\n💡 筆記特點：")
    print("  • 完整保留演講者內容（非摘要）")
    print("  • 專業術語潤稿和修正")
    print("  • 階層化結構組織")
    print("  • 重點標記（粗體、斜體、底線）")
    print("  • 根據議程文件組織內容")
    
    print("\n📍 筆記文件位置：")
    print("  各會議文件夾中的 transcription-*_detailed_notes.md")
    
    print("\n✅ 批次處理全部完成！")


if __name__ == "__main__":
    main()