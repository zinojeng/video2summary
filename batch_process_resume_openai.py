#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量處理剩餘的幻燈片文件夾 - OpenAI 版本
支持從上次中斷的地方繼續
"""

import os
import sys
import json
import time
from pathlib import Path
from markitdown_helper import convert_images_to_markdown


def load_progress():
    """載入進度文件"""
    progress_file = "batch_progress_openai.json"
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {"processed": [], "failed": [], "skipped": []}


def save_progress(progress):
    """保存進度"""
    with open("batch_progress_openai.json", 'w') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def find_slide_folders(base_path):
    """查找所有 slides 文件夾"""
    folders = []
    for folder in Path(base_path).rglob('*_slides'):
        if folder.name != 'selected_slides' and folder.is_dir():
            folders.append(str(folder))
    return sorted(folders)


def check_existing_analysis(folder_path):
    """檢查是否已有分析文件"""
    files_to_check = [
        'selected_slides_analysis.md',
        'slides_analysis.md',
        'selected_slides_analysis_gemini.md',
        'slides_analysis_gemini.md'
    ]
    
    existing = []
    for filename in files_to_check:
        if os.path.exists(os.path.join(folder_path, filename)):
            existing.append(filename)
    
    return existing


def process_folder(folder_path, api_key, model="gpt-4o-mini"):
    """處理單個文件夾的 selected_slides"""
    selected_path = os.path.join(folder_path, 'selected_slides')
    if not os.path.exists(selected_path):
        return False, "No selected_slides"
    
    # 檢查是否已有 OpenAI 分析文件
    output_file = os.path.join(folder_path, 'selected_slides_analysis.md')
    if os.path.exists(output_file):
        return True, "Already analyzed with OpenAI"
    
    # 獲取圖片
    images = []
    for f in sorted(os.listdir(selected_path)):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
            images.append(os.path.join(selected_path, f))
    
    if not images:
        return False, "No images found"
    
    parent_dir = os.path.basename(os.path.dirname(folder_path))
    title = f"{parent_dir} - 精選幻燈片分析"
    
    print(f"  找到 {len(images)} 張圖片")
    print(f"  使用模型: {model}")
    
    # 分析
    try:
        success, _, info = convert_images_to_markdown(
            image_paths=images,
            output_file=output_file,
            title=title,
            use_llm=True,
            api_key=api_key,
            model=model
        )
        
        if success:
            return True, f"成功處理 {info.get('processed_images', len(images))} 張圖片"
        else:
            return False, info.get('error', 'Unknown error')
    
    except Exception as e:
        return False, str(e)


def main():
    if len(sys.argv) < 3:
        print("用法: python batch_process_resume_openai.py <path> <api_key> [--yes]")
        sys.exit(1)
    
    base_path = sys.argv[1]
    api_key = sys.argv[2]
    auto_confirm = len(sys.argv) > 3 and sys.argv[3] == '--yes'
    
    print("\n🤖 OpenAI 批量幻燈片分析工具")
    print("="*60)
    print("模型: GPT-4o-mini")
    print("模式: 精選幻燈片分析")
    print("="*60)
    
    # 載入進度
    progress = load_progress()
    
    # 查找所有文件夾
    all_folders = find_slide_folders(base_path)
    print(f"\n找到 {len(all_folders)} 個幻燈片文件夾")
    
    # 檢查每個文件夾的狀態
    need_process = []
    already_done = []
    
    for folder in all_folders:
        folder_name = os.path.basename(folder)
        existing = check_existing_analysis(folder)
        
        if 'selected_slides_analysis.md' in existing:
            already_done.append(folder)
        elif folder not in progress['failed']:
            need_process.append(folder)
    
    print(f"已完成 OpenAI 分析: {len(already_done)} 個")
    print(f"需要處理: {len(need_process)} 個")
    print(f"之前失敗: {len(progress['failed'])} 個")
    
    if not need_process:
        print("\n✅ 所有文件夾都已完成 OpenAI 分析！")
        return
    
    # 確認處理
    print(f"\n將處理 {len(need_process)} 個文件夾")
    if not auto_confirm:
        confirm = input("確定開始處理？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消")
            return
    
    # 開始處理
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for i, folder in enumerate(need_process, 1):
        folder_name = os.path.basename(folder)
        parent_name = os.path.basename(os.path.dirname(folder))
        
        print(f"\n[{i}/{len(need_process)}] 處理: {parent_name}/{folder_name}")
        
        try:
            success, message = process_folder(folder, api_key)
            
            if success:
                if "Already analyzed" not in message:
                    print(f"  ✅ {message}")
                    progress['processed'].append(folder)
                    processed_count += 1
                else:
                    print(f"  ⏭️  {message}")
                    progress['skipped'].append(folder)
            else:
                print(f"  ❌ 失敗: {message}")
                progress['failed'].append(folder)
                failed_count += 1
            
            # 保存進度
            save_progress(progress)
            
            # 顯示統計
            elapsed = time.time() - start_time
            total_done = len(progress['processed'])
            
            if i < len(need_process):
                avg_time = elapsed / i
                remaining = len(need_process) - i
                eta = avg_time * remaining
                
                print(f"\n進度: {i}/{len(need_process)} ({i/len(need_process)*100:.1f}%)")
                print(f"已用時: {elapsed/60:.1f} 分鐘")
                print(f"預計剩餘: {eta/60:.1f} 分鐘")
                print(f"平均處理時間: {avg_time:.1f} 秒/文件夾")
            
            # 短暫延遲避免太快
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用戶中斷！進度已保存。")
            save_progress(progress)
            break
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            progress['failed'].append(folder)
            failed_count += 1
            save_progress(progress)
    
    # 完成統計
    total_time = time.time() - start_time
    print("\n" + "="*60)
    print("📊 處理完成統計")
    print("="*60)
    print(f"本次處理: {processed_count} 個成功, {failed_count} 個失敗")
    print(f"總共完成: {len(progress['processed'])} 個")
    print(f"總共失敗: {len(progress['failed'])} 個")
    print(f"總用時: {total_time/60:.1f} 分鐘")
    
    if processed_count > 0:
        print(f"平均處理時間: {total_time/processed_count:.1f} 秒/文件夾")
    
    # 顯示失敗的文件夾
    if progress['failed']:
        print(f"\n❌ 失敗的文件夾 ({len(progress['failed'])} 個):")
        for folder in progress['failed'][-10:]:  # 只顯示最近10個
            print(f"  - {os.path.basename(folder)}")
        
        if len(progress['failed']) > 10:
            print(f"  ... 還有 {len(progress['failed']) - 10} 個")
    
    print("\n✅ 批量處理完成！")
    print(f"分析文件已保存為: selected_slides_analysis.md")


if __name__ == "__main__":
    main()