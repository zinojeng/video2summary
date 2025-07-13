#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重新排序並重命名幻燈片文件
確保按時間順序排列
"""

import os
import re
import shutil
import json
from pathlib import Path


def extract_timestamp(filename):
    """從文件名中提取時間戳"""
    # 匹配不同格式的時間戳
    patterns = [
        r'_t(\d+\.?\d*)s',  # 標準格式: _t123.4s
        r'_(\d+\.?\d*)s',   # 簡化格式: _123.4s
        r't(\d+\.?\d*)',    # 無s格式: t123.4
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return float(match.group(1))
    
    return 0.0


def reorder_slides(folder_path, backup=True):
    """重新排序並重命名文件夾中的幻燈片"""
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"錯誤：文件夾不存在 - {folder_path}")
        return False
    
    # 獲取所有圖片文件
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in folder.iterdir() 
                   if f.is_file() and f.suffix.lower() in image_extensions]
    
    if not image_files:
        print("沒有找到圖片文件")
        return False
    
    print(f"找到 {len(image_files)} 張圖片")
    
    # 提取時間戳並排序
    files_with_time = []
    for f in image_files:
        timestamp = extract_timestamp(f.name)
        files_with_time.append((timestamp, f))
    
    # 按時間戳排序
    files_with_time.sort(key=lambda x: x[0])
    
    # 備份原始文件（如果需要）
    if backup:
        backup_folder = folder / "original_order"
        backup_folder.mkdir(exist_ok=True)
        print(f"備份原始文件到: {backup_folder}")
        
        for _, f in files_with_time:
            shutil.copy2(f, backup_folder / f.name)
    
    # 重新命名文件
    print("\n重新命名文件...")
    renamed_files = []
    
    for idx, (timestamp, old_file) in enumerate(files_with_time, 1):
        # 生成新文件名
        minutes = int(timestamp / 60)
        seconds = timestamp % 60
        
        # 保留原始的哈希值（如果有）
        hash_match = re.search(r'_h([a-f0-9]+)', old_file.name)
        hash_str = f"_h{hash_match.group(1)}" if hash_match else ""
        
        # 新文件名格式: slide_001_t0m30.5s_h12345678.jpg
        new_name = f"slide_{idx:03d}_t{minutes}m{seconds:.1f}s{hash_str}{old_file.suffix}"
        new_path = folder / new_name
        
        # 重命名文件
        old_file.rename(new_path)
        renamed_files.append({
            'old_name': old_file.name,
            'new_name': new_name,
            'timestamp': timestamp,
            'index': idx
        })
        
        print(f"{idx:3d}. {old_file.name} -> {new_name} (時間: {minutes}:{seconds:05.1f})")
    
    # 更新元數據文件（如果存在）
    metadata_file = folder / "slides_metadata.json"
    if metadata_file.exists():
        print("\n更新元數據文件...")
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 創建文件名映射
        name_mapping = {item['old_name']: item for item in renamed_files}
        
        # 更新slides數組
        if 'slides' in metadata:
            # 按時間戳重新排序
            metadata['slides'].sort(key=lambda x: x.get('timestamp', 0))
            
            # 更新索引和文件名
            for idx, slide in enumerate(metadata['slides'], 1):
                old_filename = slide.get('filename', '')
                if old_filename in name_mapping:
                    slide['index'] = idx
                    slide['filename'] = name_mapping[old_filename]['new_name']
        
        # 保存更新的元數據
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print("元數據已更新")
    
    print(f"\n完成！已重新排序 {len(renamed_files)} 張幻燈片")
    return True


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python reorder_slides.py <幻燈片文件夾路徑> [--no-backup]")
        print("\n參數說明:")
        print("  <幻燈片文件夾路徑>: 包含幻燈片圖片的文件夾")
        print("  --no-backup: 不備份原始文件")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    backup = "--no-backup" not in sys.argv
    
    reorder_slides(folder_path, backup)


if __name__ == "__main__":
    main()