#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試感知哈希和去重功能
"""

import os
import sys
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_test_slides():
    """創建測試幻燈片圖片"""
    test_dir = "test_slides_phash"
    os.makedirs(test_dir, exist_ok=True)
    
    # 創建一些測試圖片
    slides = []
    
    # 1. 原始幻燈片
    img1 = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img1)
    draw.rectangle([50, 50, 750, 550], fill='lightblue')
    draw.text((300, 250), "Slide 1: Original", fill='black', font=None)
    img1.save(os.path.join(test_dir, "slide_01.jpg"))
    slides.append(("slide_01.jpg", "Original slide"))
    
    # 2. 完全相同的副本
    img1.save(os.path.join(test_dir, "slide_02_duplicate.jpg"))
    slides.append(("slide_02_duplicate.jpg", "Exact duplicate of slide 1"))
    
    # 3. 略有不同（添加小噪點）
    img3 = img1.copy()
    pixels = img3.load()
    for i in range(10):
        x = np.random.randint(0, 800)
        y = np.random.randint(0, 600)
        pixels[x, y] = (255, 0, 0)  # 添加紅色噪點
    img3.save(os.path.join(test_dir, "slide_03_noise.jpg"))
    slides.append(("slide_03_noise.jpg", "Slide 1 with minor noise"))
    
    # 4. 完全不同的幻燈片
    img4 = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img4)
    draw.rectangle([50, 50, 750, 550], fill='lightgreen')
    draw.text((300, 250), "Slide 2: Different", fill='black', font=None)
    img4.save(os.path.join(test_dir, "slide_04_different.jpg"))
    slides.append(("slide_04_different.jpg", "Completely different slide"))
    
    # 5. 調整亮度的版本
    img5 = img1.copy()
    img5 = Image.eval(img5, lambda x: int(x * 0.8))  # 降低亮度
    img5.save(os.path.join(test_dir, "slide_05_darker.jpg"))
    slides.append(("slide_05_darker.jpg", "Slide 1 with reduced brightness"))
    
    # 6. 稍微縮放的版本
    img6 = img1.resize((790, 590))
    img6_canvas = Image.new('RGB', (800, 600), color='white')
    img6_canvas.paste(img6, (5, 5))
    img6_canvas.save(os.path.join(test_dir, "slide_06_scaled.jpg"))
    slides.append(("slide_06_scaled.jpg", "Slide 1 slightly scaled"))
    
    return test_dir, slides


def test_phash_similarity():
    """測試感知哈希相似度計算"""
    # 動態導入需要的函數
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from video_audio_processor import calculate_phash
    from improved_slide_capture import ImprovedSlideCapture
    
    test_dir, slides = create_test_slides()
    
    print("=== 測試感知哈希相似度 ===\n")
    
    # 計算所有圖片的哈希值
    hashes = {}
    for filename, description in slides:
        filepath = os.path.join(test_dir, filename)
        img = cv2.imread(filepath)
        phash = calculate_phash(img)
        hashes[filename] = (phash, description)
        print(f"{filename}: {phash} ({description})")
    
    print("\n=== 相似度比較 ===\n")
    
    # 創建一個臨時的 ImprovedSlideCapture 實例來使用其方法
    temp_capture = ImprovedSlideCapture("dummy", "dummy", 0.85)
    
    # 比較所有圖片對
    filenames = list(hashes.keys())
    for i in range(len(filenames)):
        for j in range(i + 1, len(filenames)):
            file1, file2 = filenames[i], filenames[j]
            hash1, desc1 = hashes[file1]
            hash2, desc2 = hashes[file2]
            
            similarity = temp_capture.calculate_phash_similarity(hash1, hash2)
            
            print(f"{file1} vs {file2}:")
            print(f"  相似度: {similarity:.2%}")
            print(f"  判定: {'相似' if similarity > 0.9 else '不同'}")
            print()
    
    # 清理
    import shutil
    shutil.rmtree(test_dir)
    print("測試完成，已清理測試文件")


def test_metadata_generation():
    """測試元數據生成功能"""
    print("\n=== 測試元數據生成 ===\n")
    
    # 創建測試元數據
    metadata = {
        "video_path": "/path/to/test_video.mp4",
        "total_frames": 3000,
        "fps": 30.0,
        "threshold": 0.85,
        "slides": [
            {
                "index": 1,
                "filename": "slide_001_t5.0s_h12345678.jpg",
                "frame_index": 150,
                "timestamp": 5.0,
                "phash": "1234567890abcdef"
            },
            {
                "index": 2,
                "filename": "slide_g01_002_t10.0s_habcdef12.jpg",
                "frame_index": 300,
                "timestamp": 10.0,
                "phash": "abcdef1234567890",
                "group_id": 1,
                "similar_frames": [(280, "abcdef1234567889"), (320, "abcdef1234567891")]
            }
        ],
        "similarity_groups": {
            "1": [(280, "abcdef1234567889"), (300, "abcdef1234567890"), (320, "abcdef1234567891")]
        }
    }
    
    # 保存為 JSON
    test_metadata_path = "test_metadata.json"
    with open(test_metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"元數據已保存到: {test_metadata_path}")
    
    # 讀取並顯示
    with open(test_metadata_path, 'r', encoding='utf-8') as f:
        loaded_metadata = json.load(f)
    
    print("\n元數據內容:")
    print(f"- 視頻路徑: {loaded_metadata['video_path']}")
    print(f"- 總幀數: {loaded_metadata['total_frames']}")
    print(f"- FPS: {loaded_metadata['fps']}")
    print(f"- 幻燈片數量: {len(loaded_metadata['slides'])}")
    
    if 'similarity_groups' in loaded_metadata:
        print(f"- 相似組數量: {len(loaded_metadata['similarity_groups'])}")
        for group_id, frames in loaded_metadata['similarity_groups'].items():
            print(f"  - 組 {group_id}: {len(frames)} 個相似幀")
    
    # 清理
    os.remove(test_metadata_path)
    print("\n測試完成，已清理測試文件")


if __name__ == "__main__":
    print("開始測試新的感知哈希和元數據功能...\n")
    
    test_phash_similarity()
    test_metadata_generation()
    
    print("\n所有測試完成！")
    print("\n新功能說明:")
    print("1. 文件命名格式:")
    print("   - 標準: slide_001_t10.5s_h12345678.jpg")
    print("   - 分組: slide_g01_001_t10.5s_h12345678.jpg")
    print("   - 包含: 序號、時間戳、哈希前8位")
    print("\n2. 重複檢測:")
    print("   - 使用感知哈希(pHash)而非MD5")
    print("   - 能檢測相似但不完全相同的圖片")
    print("   - 相似度閾值可調整")
    print("\n3. 元數據文件:")
    print("   - 保存為 slides_metadata.json")
    print("   - 包含完整的幻燈片信息")
    print("   - 記錄相似度分組關係")