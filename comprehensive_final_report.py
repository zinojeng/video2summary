#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
綜合最終報告 - 包括所有類型的分析
"""

import os
import json
from pathlib import Path
from datetime import datetime


def find_all_analysis_files(base_path):
    """查找所有分析文件"""
    analysis_files = {
        'selected_slides_analysis.md': [],
        'selected_slides_analysis_gemini.md': [],
        'slides_analysis.md': [],
        'slides_analysis_gemini.md': []
    }
    
    for filename in analysis_files.keys():
        for file_path in Path(base_path).rglob(filename):
            analysis_files[filename].append(str(file_path))
    
    return analysis_files


def main():
    base_path = "/Volumes/WD_BLACK/國際年會/ADA2025"
    
    print("\n📊 ADA2025 幻燈片分析綜合最終報告")
    print("="*80)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 查找所有分析文件
    analysis_files = find_all_analysis_files(base_path)
    
    # 統計
    stats = {
        'OpenAI精選分析': len(analysis_files['selected_slides_analysis.md']),
        'Gemini精選分析': len(analysis_files['selected_slides_analysis_gemini.md']),
        'OpenAI完整分析': len(analysis_files['slides_analysis.md']),
        'Gemini完整分析': len(analysis_files['slides_analysis_gemini.md'])
    }
    
    # 顯示統計
    print("\n📈 分析文件統計：")
    for analysis_type, count in stats.items():
        print(f"  {analysis_type}: {count} 個文件")
    
    # 查找所有 slides 文件夾
    all_slides_folders = []
    for folder in Path(base_path).rglob('*_slides'):
        if folder.name != 'selected_slides' and folder.is_dir():
            all_slides_folders.append(str(folder))
    
    total_folders = len(all_slides_folders)
    
    # 計算覆蓋率
    folders_with_any_analysis = set()
    for file_list in analysis_files.values():
        for file_path in file_list:
            parent_folder = os.path.dirname(file_path)
            # 處理 CGM 特殊情況
            if 'CGM in Action' in parent_folder and parent_folder.endswith(('Center', 'University', 'Association')):
                folders_with_any_analysis.add(parent_folder)
            else:
                # 找到對應的 _slides 文件夾
                for folder in all_slides_folders:
                    if parent_folder.startswith(folder):
                        folders_with_any_analysis.add(folder)
                        break
    
    coverage = (len(folders_with_any_analysis) / total_folders * 100) if total_folders > 0 else 0
    
    print(f"\n📊 整體覆蓋率：")
    print(f"  總幻燈片文件夾: {total_folders} 個")
    print(f"  已分析文件夾: {len(folders_with_any_analysis)} 個")
    print(f"  覆蓋率: {coverage:.1f}%")
    
    # 特殊文件夾統計
    cgm_speaker_analyses = 0
    for file_path in analysis_files['slides_analysis.md']:
        if 'CGM in Action' in file_path and any(x in file_path for x in ['1. Older', '2. The Effectiveness', '3. The Libre', '4. Short-Term']):
            cgm_speaker_analyses += 1
    
    print(f"\n📌 特殊處理：")
    print(f"  CGM 演講者個別分析: {cgm_speaker_analyses} 個")
    print(f"  無 selected_slides 的文件夾完整分析: {stats['OpenAI完整分析'] - cgm_speaker_analyses} 個")
    
    # 生成詳細報告
    detailed_report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': {
            'total_slides_folders': total_folders,
            'analyzed_folders': len(folders_with_any_analysis),
            'coverage_percentage': round(coverage, 2),
            'analysis_breakdown': stats,
            'special_cases': {
                'cgm_speaker_analyses': cgm_speaker_analyses,
                'full_folder_analyses': stats['OpenAI完整分析'] - cgm_speaker_analyses
            }
        },
        'analysis_files': {k: len(v) for k, v in analysis_files.items()},
        'summary': {
            'openai_total': stats['OpenAI精選分析'] + stats['OpenAI完整分析'],
            'gemini_total': stats['Gemini精選分析'] + stats['Gemini完整分析']
        }
    }
    
    # 保存報告
    with open('comprehensive_final_report.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_report, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 分析總結：")
    print(f"  1. 已完成 {total_folders} 個幻燈片文件夾中的 {len(folders_with_any_analysis)} 個分析")
    print(f"  2. OpenAI 總共分析了 {detailed_report['summary']['openai_total']} 個文件夾")
    print(f"  3. Gemini 總共分析了 {detailed_report['summary']['gemini_total']} 個文件夾")
    print(f"  4. 特別處理了 CGM 演講者個別文件夾和無 selected_slides 的文件夾")
    print(f"\n📄 詳細報告已保存到: comprehensive_final_report.json")


if __name__ == "__main__":
    main()