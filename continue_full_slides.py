#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
繼續處理剩餘的完整 slides 文件夾
"""

import os
import sys
import time
from markitdown_helper import convert_images_to_markdown
from model_config import OPENAI_VISION


def process_full_slides_folder(folder_path, api_key, model=OPENAI_VISION):
    """處理完整的 slides 文件夾"""
    
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
    
    # 限制圖片數量以控制成本（最多30張）
    if len(images) > 30:
        print(f"  ⚠️  找到 {len(images)} 張圖片，限制為前 30 張")
        images = images[:30]
    
    parent_dir = os.path.basename(os.path.dirname(folder_path))
    title = f"{parent_dir} - 幻燈片分析"
    
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
    if len(sys.argv) < 2:
        print("用法: python continue_full_slides.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # 檢查哪些還需要處理
    remaining_folders = []
    
    # 檢查一般文件夾
    folders_to_check = [
        "/Volumes/WD_BLACK/國際年會/ADA2025/Diabetic Neuropathy—Unraveling Pain Mechanisms, Systemic Complications, and Innovations in Prevention and Treatment (With ADA Presidents' Select Abstract Presentation)/Diabetic Neuropathy—Unraveling Pain Mechanisms, Systemic Complications, and Innovations in Prevention and Treatment (With ADA Presidents' Select Abstract Presentation)/Diabetic Neuropathy—Unraveling Pain Mechanisms, Systemic Complications, and Innovations in Prevention and Treatment (With ADA Presidents' Select Abstract Presentation)_slides",
        "/Volumes/WD_BLACK/國際年會/ADA2025/Interoception—Brain–Body Communication Controls Metabolism/Interoception—Brain–Body Communication Controls Metabolism/Interoception—Brain–Body Communication Controls Metabolism _slides",
        "/Volumes/WD_BLACK/國際年會/ADA2025/Mechanisms Linking Adipose Health with Lipid and Glucose Homeostasis/Mechanisms Linking Adipose Health with Lipid and Glucose Homeostasis/Mechanisms Linking Adipose Health with Lipid and Glucose Homeostasis _slides"
    ]
    
    for folder in folders_to_check:
        if os.path.exists(folder) and not os.path.exists(os.path.join(folder, 'slides_analysis.md')):
            remaining_folders.append(folder)
    
    # 檢查 CGM 文件夾
    cgm_base = "/Volumes/WD_BLACK/國際年會/ADA2025/CGM in Action—Smarter Choices, Better Balance, Lasting Impact"
    cgm_folders = [
        "1. Older Adults with Diabetes Require Longer Time to Initiate and Maintain CGM Technology with Use of Remote Education Elena Toschi Joslin Diabetes Center",
        "2. The Effectiveness of Personalized Dietary Advice Based on CGM Data for Newly Diagnosed Patients with Type 2 Diabetes Heng Wan Shunde Hospital, Southern Medical University",
        "3. The Libre Enabled Reduction of A1C through Effective Eating and Exercise Study—LIBERATE CANADA Sonja Reichert Western University",
        "4. Short-Term Continuous Glucose Monitoring Reveals Insights and Promotes Behavioral Awareness in People with Non-Insulin-Treated Type 2 Diabetes, Even after Minimal Instructions Tanja Thybo Danish Diabetes Association"
    ]
    
    cgm_to_process = []
    for cgm_folder in cgm_folders:
        folder_path = os.path.join(cgm_base, cgm_folder)
        if os.path.exists(folder_path):
            # 查找 slides 子文件夾
            for item in os.listdir(folder_path):
                if item.endswith('_slides') and os.path.isdir(os.path.join(folder_path, item)):
                    slides_folder = os.path.join(folder_path, item)
                    if not os.path.exists(os.path.join(slides_folder, 'slides_analysis.md')):
                        cgm_to_process.append((cgm_folder, slides_folder))
                    break
    
    total_remaining = len(remaining_folders) + len(cgm_to_process)
    
    if total_remaining == 0:
        print("✅ 所有文件夾都已處理完成！")
        return
    
    print(f"\n🤖 繼續處理剩餘的 {total_remaining} 個文件夾")
    print("="*60)
    
    # 處理剩餘的一般文件夾
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for i, folder in enumerate(remaining_folders, 1):
        folder_name = os.path.basename(folder)
        print(f"\n[{i}/{total_remaining}] 處理: {folder_name}")
        
        try:
            success, message = process_full_slides_folder(folder, api_key)
            
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
    
    # 處理 CGM 文件夾
    for j, (cgm_name, slides_folder) in enumerate(cgm_to_process, 1):
        i = len(remaining_folders) + j
        print(f"\n[{i}/{total_remaining}] 處理 CGM: {cgm_name}")
        print(f"  Slides 文件夾: {os.path.basename(slides_folder)}")
        
        try:
            success, message = process_full_slides_folder(slides_folder, api_key)
            
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
    
    print("\n✅ 批量處理完成！")


if __name__ == "__main__":
    main()