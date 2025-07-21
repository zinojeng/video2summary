#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量處理剩餘的幻燈片文件夾
支持從上次中斷的地方繼續
"""

import os
import sys
import json
import time
from pathlib import Path
from markitdown_helper_gemini import convert_images_to_markdown_gemini


def load_progress():
    """載入進度文件"""
    progress_file = "batch_progress.json"
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {"processed": [], "failed": []}


def save_progress(progress):
    """保存進度"""
    with open("batch_progress.json", 'w') as f:
        json.dump(progress, f, indent=2)


def find_slide_folders(base_path):
    """查找所有 slides 文件夾"""
    folders = []
    for folder in Path(base_path).rglob('*_slides'):
        if folder.name != 'selected_slides' and folder.is_dir():
            folders.append(str(folder))
    return sorted(folders)


def process_folder(folder_path, api_key, model="gemini-2.0-flash-exp"):
    """處理單個文件夾的 selected_slides"""
    selected_path = os.path.join(folder_path, 'selected_slides')
    if not os.path.exists(selected_path):
        return False, "No selected_slides"
    
    # 檢查是否已有分析文件
    output_file = os.path.join(folder_path, 'selected_slides_analysis_gemini.md')
    if os.path.exists(output_file):
        return True, "Already analyzed"
    
    # 獲取圖片
    images = []
    for f in sorted(os.listdir(selected_path)):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
            images.append(os.path.join(selected_path, f))
    
    if not images:
        return False, "No images found"
    
    parent_dir = os.path.basename(os.path.dirname(folder_path))
    title = f"{parent_dir} - 精選幻燈片分析 (Gemini)"
    
    print(f"  找到 {len(images)} 張圖片")
    print(f"  預計時間: {len(images) * 6 / 60:.1f} 分鐘")
    
    # 分析
    success, _, info = convert_images_to_markdown_gemini(
        image_paths=images,
        output_file=output_file,
        title=title,
        use_llm=True,
        api_key=api_key,
        model=model
    )
    
    return success, info.get('error', 'Success') if not success else f"Processed {len(images)} images"


def main():
    if len(sys.argv) < 3:
        print("用法: python batch_process_resume.py <path> <api_key>")
        sys.exit(1)
    
    base_path = sys.argv[1]
    api_key = sys.argv[2]
    
    # 載入進度
    progress = load_progress()
    
    # 查找所有文件夾
    all_folders = find_slide_folders(base_path)
    print(f"找到 {len(all_folders)} 個幻燈片文件夾")
    
    # 過濾已處理的
    remaining = [f for f in all_folders if f not in progress['processed'] and f not in progress['failed']]
    print(f"剩餘待處理: {len(remaining)} 個")
    
    if not remaining:
        print("所有文件夾都已處理完成！")
        return
    
    # 開始處理
    start_time = time.time()
    
    for i, folder in enumerate(remaining, 1):
        print(f"\n[{i}/{len(remaining)}] 處理: {os.path.basename(folder)}")
        
        try:
            success, message = process_folder(folder, api_key)
            
            if success:
                if "Already analyzed" not in message:
                    print(f"  ✅ 成功: {message}")
                    progress['processed'].append(folder)
                else:
                    print(f"  ⏭️  跳過: {message}")
                    progress['processed'].append(folder)
            else:
                print(f"  ❌ 失敗: {message}")
                progress['failed'].append(folder)
            
            # 保存進度
            save_progress(progress)
            
            # 顯示統計
            total_processed = len(progress['processed'])
            total_failed = len(progress['failed'])
            elapsed = time.time() - start_time
            
            print(f"\n統計: 已處理 {total_processed}, 失敗 {total_failed}")
            print(f"已用時: {elapsed/60:.1f} 分鐘")
            
            if i < len(remaining):
                eta = (elapsed / i) * (len(remaining) - i)
                print(f"預計剩餘: {eta/60:.1f} 分鐘")
            
        except KeyboardInterrupt:
            print("\n\n用戶中斷！進度已保存。")
            save_progress(progress)
            sys.exit(0)
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            progress['failed'].append(folder)
            save_progress(progress)
    
    # 完成
    print("\n" + "="*60)
    print("處理完成！")
    print(f"總共處理: {len(progress['processed'])} 個")
    print(f"失敗: {len(progress['failed'])} 個")
    print(f"總用時: {(time.time() - start_time)/60:.1f} 分鐘")


if __name__ == "__main__":
    main()