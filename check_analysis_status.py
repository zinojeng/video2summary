#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
檢查分析狀態
"""

import os
import json
from pathlib import Path


def find_all_slides_folders(base_path):
    """查找所有 slides 文件夾"""
    folders = []
    for folder in Path(base_path).rglob('*_slides'):
        if folder.name != 'selected_slides' and folder.is_dir():
            folders.append(str(folder))
    return sorted(folders)


def check_analysis_files(folder):
    """檢查分析文件是否存在"""
    files = {
        'selected_gemini': os.path.join(folder, 'selected_slides_analysis_gemini.md'),
        'full_gemini': os.path.join(folder, 'slides_analysis_gemini.md'),
        'selected_openai': os.path.join(folder, 'selected_slides_analysis.md'),
        'full_openai': os.path.join(folder, 'slides_analysis.md')
    }
    
    exists = {}
    for key, path in files.items():
        exists[key] = os.path.exists(path)
    
    return exists


def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    # 查找所有文件夾
    all_folders = find_all_slides_folders(base_path)
    print(f"總共找到 {len(all_folders)} 個幻燈片文件夾\n")
    
    # 載入進度文件
    progress = {"processed": [], "failed": []}
    if os.path.exists("batch_progress.json"):
        with open("batch_progress.json", 'r') as f:
            progress = json.load(f)
    
    # 統計
    stats = {
        'total': len(all_folders),
        'has_selected_gemini': 0,
        'has_full_gemini': 0,
        'has_any_analysis': 0,
        'no_analysis': 0,
        'in_progress': len(progress['processed']),
        'failed': len(progress['failed'])
    }
    
    print("分析狀態：")
    print("="*80)
    
    no_analysis = []
    
    for i, folder in enumerate(all_folders, 1):
        folder_name = os.path.basename(folder)
        parent_name = os.path.basename(os.path.dirname(folder))
        
        # 檢查分析文件
        exists = check_analysis_files(folder)
        
        # 統計
        if exists['selected_gemini']:
            stats['has_selected_gemini'] += 1
        if exists['full_gemini']:
            stats['has_full_gemini'] += 1
        
        has_any = any(exists.values())
        if has_any:
            stats['has_any_analysis'] += 1
        else:
            stats['no_analysis'] += 1
            no_analysis.append(folder)
        
        # 顯示狀態
        status = []
        if exists['selected_gemini']:
            status.append("✅ Selected(Gemini)")
        if exists['full_gemini']:
            status.append("✅ Full(Gemini)")
        if exists['selected_openai']:
            status.append("📄 Selected(OpenAI)")
        if exists['full_openai']:
            status.append("📄 Full(OpenAI)")
        
        if not status:
            status = ["❌ 無分析"]
        
        print(f"{i:2d}. {parent_name}/{folder_name}")
        print(f"    {' | '.join(status)}")
    
    # 顯示統計
    print("\n" + "="*80)
    print("統計摘要：")
    print(f"  總文件夾數: {stats['total']}")
    print(f"  已完成 Gemini 精選分析: {stats['has_selected_gemini']}")
    print(f"  已完成 Gemini 完整分析: {stats['has_full_gemini']}")
    print(f"  有任何分析: {stats['has_any_analysis']}")
    print(f"  無任何分析: {stats['no_analysis']}")
    print(f"  進度文件中已處理: {stats['in_progress']}")
    print(f"  進度文件中失敗: {stats['failed']}")
    
    # 顯示未分析的文件夾
    if no_analysis:
        print(f"\n未分析的文件夾 ({len(no_analysis)} 個)：")
        for folder in no_analysis:
            print(f"  - {os.path.basename(os.path.dirname(folder))}/{os.path.basename(folder)}")
    
    # 計算預估時間
    remaining = stats['total'] - stats['has_selected_gemini']
    if remaining > 0:
        # 假設每個文件夾平均 30 張圖片，每張 6 秒
        estimated_time = remaining * 30 * 6 / 60
        print(f"\n預估剩餘時間: {estimated_time:.1f} 分鐘 ({estimated_time/60:.1f} 小時)")


if __name__ == "__main__":
    main()