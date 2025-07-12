#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
轉錄筆記處理最終報告
"""

import os
import json
from pathlib import Path
from datetime import datetime


def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print("\n📊 ADA2025 轉錄筆記處理最終報告")
    print("="*80)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 載入進度
    progress_file = 'transcription_notes_progress_v2.json'
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        print("找不到進度文件")
        return
    
    # 統計
    print("\n📈 處理統計：")
    print(f"  ✅ 成功處理: {len(progress['processed'])} 個文件")
    print(f"  ❌ 處理失敗: {len(progress['failed'])} 個文件")
    print(f"  💰 總 Token 使用: {progress['stats'].get('total_tokens', 0):,}")
    
    # 計算成本（估算）
    # Gemini 2.5 Pro 價格約為 $7.5/百萬 tokens
    total_tokens = progress['stats'].get('total_tokens', 0)
    estimated_cost = (total_tokens / 1_000_000) * 7.5
    print(f"  💵 估計成本: ${estimated_cost:.2f} USD")
    
    # 查找生成的筆記文件
    notes_files = list(Path(base_path).rglob('*_detailed_notes.md'))
    print(f"\n📝 生成的筆記文件: {len(notes_files)} 個")
    
    # 按文件夾分組顯示
    folder_notes = {}
    for note_file in notes_files:
        folder_name = note_file.parent.name
        if folder_name not in folder_notes:
            folder_notes[folder_name] = []
        folder_notes[folder_name].append(note_file.name)
    
    print("\n📁 各文件夾的筆記：")
    for i, (folder, notes) in enumerate(sorted(folder_notes.items()), 1):
        print(f"\n{i}. {folder}")
        for note in notes:
            print(f"   - {note}")
    
    # 處理的文件類型統計
    txt_count = sum(1 for f in progress['processed'] if f.endswith('.txt'))
    srt_count = sum(1 for f in progress['processed'] if f.endswith('.srt'))
    
    print(f"\n📊 文件類型統計：")
    print(f"  TXT 文件: {txt_count} 個")
    print(f"  SRT 文件: {srt_count} 個")
    
    # 找出有議程的文件
    agenda_count = 0
    for note_file in notes_files:
        with open(note_file, 'r', encoding='utf-8') as f:
            content = f.read(500)  # 讀取前500字符
            if '*參考議程：' in content:
                agenda_count += 1
    
    print(f"\n📋 議程匹配：")
    print(f"  有議程文件: {agenda_count} 個")
    print(f"  無議程文件: {len(notes_files) - agenda_count} 個")
    
    # 保存最終報告
    report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': {
            'total_processed': len(progress['processed']),
            'total_failed': len(progress['failed']),
            'total_tokens': progress['stats'].get('total_tokens', 0),
            'estimated_cost_usd': round(estimated_cost, 2),
            'notes_generated': len(notes_files),
            'with_agenda': agenda_count,
            'file_types': {
                'txt': txt_count,
                'srt': srt_count
            }
        },
        'folders_processed': list(folder_notes.keys())
    }
    
    with open('transcription_notes_final_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 總結：")
    print(f"  1. 成功處理了 {len(progress['processed'])} 個轉錄文件")
    print(f"  2. 生成了 {len(notes_files)} 個詳細演講筆記")
    print(f"  3. 使用了 {total_tokens:,} tokens (約 ${estimated_cost:.2f})")
    print(f"  4. 所有筆記都已保存為 Markdown 格式")
    print(f"\n📄 詳細報告已保存到: transcription_notes_final_report.json")


if __name__ == "__main__":
    main()