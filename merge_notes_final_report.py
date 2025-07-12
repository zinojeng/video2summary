#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
合併筆記最終報告
"""

import os
import json
from pathlib import Path
from datetime import datetime


def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print("\n📊 演講筆記與投影片合併最終報告")
    print("="*80)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 載入進度
    progress_file = 'merge_notes_progress.json'
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        print("找不到進度文件")
        return
    
    # 查找生成的合併筆記
    merged_files = []
    for f in Path(base_path).rglob('*_merged_notes.md'):
        if not f.name.startswith('._'):
            merged_files.append(f)
    
    # 統計
    print("\n✅ 處理完成總結：")
    print(f"  • 成功處理文件夾: {len(progress['processed'])} 個")
    print(f"  • 生成合併筆記: {len(merged_files)} 個")
    print(f"  • 使用 Gemini 2.5 Pro tokens: {progress['stats'].get('total_tokens', 0):,}")
    
    # 成本估算
    total_tokens = progress['stats'].get('total_tokens', 0)
    estimated_cost = (total_tokens / 1_000_000) * 7.5
    print(f"  • 估計成本: ${estimated_cost:.2f} USD")
    
    # 列出成功合併的會議
    print(f"\n📁 成功合併的會議（{len(merged_files)} 場）：")
    folders = sorted(set(f.parent.name for f in merged_files))
    for i, folder in enumerate(folders, 1):
        print(f"  {i:2d}. {folder}")
    
    # 查找原始文件統計
    notes_count = len(list(Path(base_path).rglob('transcription-*_detailed_notes.md')))
    slides_count = len(list(Path(base_path).rglob('selected_slides_analysis.md')))
    
    print(f"\n📊 文件統計：")
    print(f"  • 演講筆記總數: {notes_count} 個")
    print(f"  • 投影片分析總數: {slides_count} 個")
    print(f"  • 成功合併: {len(merged_files)} 個")
    print(f"  • 合併率: {len(merged_files)/min(notes_count, slides_count)*100:.1f}%")
    
    print("\n💡 合併筆記特點：")
    print("  • 以演講者內容為主軸")
    print("  • 加入投影片參考標記 (參見 Slide X)")
    print("  • 底線標記補充說明 (__延伸內容__)")
    print("  • 避免重複，只補充新資訊")
    print("  • 建立演講與投影片的對應關係")
    
    print("\n📍 合併筆記位置：")
    print("  各會議文件夾中的 transcription-*_merged_notes.md")
    
    # 保存最終報告
    report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': {
            'folders_processed': len(progress['processed']),
            'merged_notes_generated': len(merged_files),
            'total_tokens': progress['stats'].get('total_tokens', 0),
            'estimated_cost_usd': round(estimated_cost, 2),
            'merge_rate': round(len(merged_files)/min(notes_count, slides_count)*100, 1)
        },
        'successful_merges': [f.parent.name for f in merged_files]
    }
    
    with open('merge_notes_final_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 詳細報告已保存到: merge_notes_final_report.json")
    
    # 顯示範例
    if merged_files:
        example = merged_files[0]
        print(f"\n📝 合併筆記範例：{example.name}")
        with open(example, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500)
            print("---")
            print(content)
            print("---")


if __name__ == "__main__":
    main()