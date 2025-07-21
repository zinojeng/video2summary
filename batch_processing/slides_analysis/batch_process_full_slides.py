#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量處理完整 slides 文件夾（非 selected_slides）
"""

import os
import sys
import json
import time
from pathlib import Path
from markitdown_helper import convert_images_to_markdown


def process_full_slides_folder(folder_path, api_key, model="gpt-4o-mini"):
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
        print("用法: python batch_process_full_slides.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # 定義要處理的文件夾
    folders_to_process = [
        "/Volumes/WD_BLACK/國際年會/ADA2025/Advancing Care for Diabetic Kidney Disease—Top Research Abstracts /Advancing Care for Diabetic Kidney Disease—Top Research Abstracts/Advancing Care for Diabetic Kidney Disease—Top Research Abstracts  _slides",
        "/Volumes/WD_BLACK/國際年會/ADA2025/Advancing Diabetic Retinopathy Care—Integrating Clinical Insights, AI, and Health Equity/Advancing Diabetic Retinopathy Care—Integrating Clinical Insights, AI, and Health Equity/Advancing Diabetic Retinopathy Care—Integrating Clinical Insights, AI, and Health Equity_slides",
        "/Volumes/WD_BLACK/國際年會/ADA2025/Diabetic Neuropathy—Unraveling Pain Mechanisms, Systemic Complications, and Innovations in Prevention and Treatment (With ADA Presidents' Select Abstract Presentation)/Diabetic Neuropathy—Unraveling Pain Mechanisms, Systemic Complications, and Innovations in Prevention and Treatment (With ADA Presidents' Select Abstract Presentation)/Diabetic Neuropathy—Unraveling Pain Mechanisms, Systemic Complications, and Innovations in Prevention and Treatment (With ADA Presidents' Select Abstract Presentation)_slides",
        "/Volumes/WD_BLACK/國際年會/ADA2025/Interoception—Brain–Body Communication Controls Metabolism/Interoception—Brain–Body Communication Controls Metabolism/Interoception—Brain–Body Communication Controls Metabolism _slides",
        "/Volumes/WD_BLACK/國際年會/ADA2025/Mechanisms Linking Adipose Health with Lipid and Glucose Homeostasis/Mechanisms Linking Adipose Health with Lipid and Glucose Homeostasis/Mechanisms Linking Adipose Health with Lipid and Glucose Homeostasis _slides"
    ]
    
    # CGM folders 需要特殊處理
    cgm_base = "/Volumes/WD_BLACK/國際年會/ADA2025/CGM in Action—Smarter Choices, Better Balance, Lasting Impact"
    cgm_folders = [
        "1. Older Adults with Diabetes Require Longer Time to Initiate and Maintain CGM Technology with Use of Remote Education Elena Toschi Joslin Diabetes Center",
        "2. The Effectiveness of Personalized Dietary Advice Based on CGM Data for Newly Diagnosed Patients with Type 2 Diabetes Heng Wan Shunde Hospital, Southern Medical University",
        "3. The Libre Enabled Reduction of A1C through Effective Eating and Exercise Study—LIBERATE CANADA Sonja Reichert Western University",
        "4. Short-Term Continuous Glucose Monitoring Reveals Insights and Promotes Behavioral Awareness in People with Non-Insulin-Treated Type 2 Diabetes, Even after Minimal Instructions Tanja Thybo Danish Diabetes Association"
    ]
    
    print("\n🤖 OpenAI 批量處理完整 slides 文件夾")
    print("="*60)
    print("模型: GPT-4o-mini")
    print("模式: 完整幻燈片分析（限制最多30張）")
    print("="*60)
    
    # 開始處理
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    # 處理一般文件夾
    for i, folder in enumerate(folders_to_process, 1):
        if not os.path.exists(folder):
            print(f"\n[{i}/9] ❌ 文件夾不存在: {folder}")
            failed_count += 1
            continue
            
        folder_name = os.path.basename(folder)
        print(f"\n[{i}/9] 處理: {folder_name}")
        
        try:
            success, message = process_full_slides_folder(folder, api_key)
            
            if success:
                print(f"  ✅ {message}")
                processed_count += 1
            else:
                print(f"  ❌ 失敗: {message}")
                failed_count += 1
                
            time.sleep(0.5)  # 短暫延遲
            
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            failed_count += 1
    
    # 處理 CGM 文件夾
    for j, cgm_folder in enumerate(cgm_folders, 1):
        i = len(folders_to_process) + j
        folder_path = os.path.join(cgm_base, cgm_folder)
        
        if not os.path.exists(folder_path):
            print(f"\n[{i}/9] ❌ 文件夾不存在: {cgm_folder}")
            failed_count += 1
            continue
        
        # 查找 slides 子文件夾
        slides_folder = None
        for item in os.listdir(folder_path):
            if item.endswith('_slides') and os.path.isdir(os.path.join(folder_path, item)):
                slides_folder = os.path.join(folder_path, item)
                break
        
        if not slides_folder:
            print(f"\n[{i}/9] ❌ 找不到 slides 子文件夾: {cgm_folder}")
            failed_count += 1
            continue
        
        print(f"\n[{i}/9] 處理 CGM: {cgm_folder}")
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
    print("分析文件已保存為: slides_analysis.md")


if __name__ == "__main__":
    main()