#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
處理 CGM 個別演講者文件夾
"""

import os
import sys
import time
from markitdown_helper import convert_images_to_markdown
from llm_provider_kit import OPENAI_VISION


def process_speaker_folder(folder_path, api_key, model=OPENAI_VISION):
    """處理個別演講者文件夾中的圖片"""
    
    # 檢查是否已有分析文件
    output_file = os.path.join(folder_path, 'slides_analysis.md')
    if os.path.exists(output_file):
        return True, "Already analyzed"
    
    # 獲取所有圖片
    images = []
    for f in sorted(os.listdir(folder_path)):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
            images.append(os.path.join(folder_path, f))
    
    if not images:
        return False, "No images found"
    
    # 限制圖片數量
    if len(images) > 20:
        print(f"  ⚠️  找到 {len(images)} 張圖片，限制為前 20 張")
        images = images[:20]
    
    # 從文件夾名稱提取標題
    folder_name = os.path.basename(folder_path)
    # 提取演講者名稱（通常在最後）
    parts = folder_name.split()
    speaker_idx = -1
    for i, part in enumerate(parts):
        if any(word in part.lower() for word in ['university', 'center', 'hospital', 'association']):
            speaker_idx = i
            break
    
    if speaker_idx > 0:
        title = ' '.join(parts[:speaker_idx-1])
    else:
        title = folder_name
    
    print(f"  找到 {len(images)} 張圖片")
    print(f"  標題: {title}")
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
    if len(sys.argv) < 2:
        print("用法: python process_cgm_speakers.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    cgm_base = "/Volumes/WD_BLACK/國際年會/ADA2025/CGM in Action—Smarter Choices, Better Balance, Lasting Impact"
    
    # CGM 演講者文件夾
    speaker_folders = [
        "1. Older Adults with Diabetes Require Longer Time to Initiate and Maintain CGM Technology with Use of Remote Education Elena Toschi Joslin Diabetes Center",
        "2. The Effectiveness of Personalized Dietary Advice Based on CGM Data for Newly Diagnosed Patients with Type 2 Diabetes Heng Wan Shunde Hospital, Southern Medical University",
        "3. The Libre Enabled Reduction of A1C through Effective Eating and Exercise Study—LIBERATE CANADA Sonja Reichert Western University",
        "4. Short-Term Continuous Glucose Monitoring Reveals Insights and Promotes Behavioral Awareness in People with Non-Insulin-Treated Type 2 Diabetes, Even after Minimal Instructions Tanja Thybo Danish Diabetes Association"
    ]
    
    print("\n🤖 OpenAI 批量處理 CGM 演講者文件夾")
    print("="*60)
    print("模型: GPT-4o-mini")
    print("模式: 個別演講者幻燈片分析")
    print("="*60)
    
    # 開始處理
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for i, speaker_folder in enumerate(speaker_folders, 1):
        folder_path = os.path.join(cgm_base, speaker_folder)
        
        if not os.path.exists(folder_path):
            print(f"\n[{i}/4] ❌ 文件夾不存在: {speaker_folder}")
            failed_count += 1
            continue
        
        print(f"\n[{i}/4] 處理演講者 {i}")
        print(f"  文件夾: {speaker_folder[:50]}...")
        
        try:
            success, message = process_speaker_folder(folder_path, api_key)
            
            if success:
                print(f"  ✅ {message}")
                processed_count += 1
            else:
                print(f"  ❌ 失敗: {message}")
                failed_count += 1
                
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            failed_count += 1
    
    # 完成統計
    total_time = time.time() - start_time
    print("\n" + "="*60)
    print("📊 處理完成統計")
    print("="*60)
    print(f"處理完成: {processed_count} 個成功, {failed_count} 個失敗")
    print(f"總用時: {total_time/60:.1f} 分鐘")
    
    if processed_count > 0:
        print(f"平均處理時間: {total_time/processed_count:.1f} 秒/文件夾")
    
    print("\n✅ CGM 演講者文件夾批量處理完成！")
    print("分析文件已保存在各自文件夾中的 slides_analysis.md")


if __name__ == "__main__":
    main()