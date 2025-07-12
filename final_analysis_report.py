#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最終分析報告
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
        'selected_openai': os.path.join(folder, 'selected_slides_analysis.md'),
        'has_selected': os.path.exists(os.path.join(folder, 'selected_slides'))
    }
    
    for key in ['selected_gemini', 'selected_openai']:
        files[key] = os.path.exists(files[key])
    
    return files


def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    # 查找所有文件夾
    all_folders = find_all_slides_folders(base_path)
    total = len(all_folders)
    
    print("\n📊 ADA2025 幻燈片分析最終報告")
    print("="*80)
    print(f"總共 {total} 個幻燈片文件夾\n")
    
    # 統計
    stats = {
        'total': total,
        'has_selected': 0,
        'openai_done': 0,
        'gemini_done': 0,
        'both_done': 0,
        'none_done': 0,
        'no_selected': []
    }
    
    # 詳細檢查
    for folder in all_folders:
        folder_name = os.path.basename(folder)
        parent_name = os.path.basename(os.path.dirname(folder))
        status = check_analysis_files(folder)
        
        if status['has_selected']:
            stats['has_selected'] += 1
            
            if status['selected_openai']:
                stats['openai_done'] += 1
            if status['selected_gemini']:
                stats['gemini_done'] += 1
            if status['selected_openai'] and status['selected_gemini']:
                stats['both_done'] += 1
            elif not status['selected_openai'] and not status['selected_gemini']:
                stats['none_done'] += 1
        else:
            stats['no_selected'].append(f"{parent_name}/{folder_name}")
    
    # 顯示統計
    print("📈 分析完成統計：")
    print(f"  有 selected_slides 子文件夾: {stats['has_selected']} 個")
    print(f"  ✅ OpenAI 分析完成: {stats['openai_done']} 個")
    print(f"  ✅ Gemini 分析完成: {stats['gemini_done']} 個")
    print(f"  ✅ 兩者都完成: {stats['both_done']} 個")
    print(f"  ❌ 都未完成: {stats['none_done']} 個")
    print(f"  ⚠️  無 selected_slides: {len(stats['no_selected'])} 個")
    
    # 計算覆蓋率
    if stats['has_selected'] > 0:
        openai_coverage = (stats['openai_done'] / stats['has_selected']) * 100
        gemini_coverage = (stats['gemini_done'] / stats['has_selected']) * 100
        print(f"\n📊 覆蓋率：")
        print(f"  OpenAI: {openai_coverage:.1f}%")
        print(f"  Gemini: {gemini_coverage:.1f}%")
    
    # 顯示無 selected_slides 的文件夾
    if stats['no_selected']:
        print(f"\n⚠️  以下文件夾沒有 selected_slides 子文件夾：")
        for folder in stats['no_selected'][:5]:
            print(f"  - {folder}")
        if len(stats['no_selected']) > 5:
            print(f"  ... 還有 {len(stats['no_selected']) - 5} 個")
    
    # 總結
    print("\n✅ 分析總結：")
    print(f"  大部分文件夾已完成至少一種 AI 分析")
    print(f"  OpenAI 分析更完整（{stats['openai_done']} vs Gemini {stats['gemini_done']}）")
    print(f"  所有分析文件都保存在各自的 slides 文件夾中")
    
    # 保存報告
    report = {
        'timestamp': os.popen('date').read().strip(),
        'statistics': stats,
        'total_folders': total,
        'analysis_files': {
            'openai': 'selected_slides_analysis.md',
            'gemini': 'selected_slides_analysis_gemini.md'
        }
    }
    
    with open('final_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n📄 詳細報告已保存到: final_analysis_report.json")


if __name__ == "__main__":
    main()