#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
幻燈片後處理工具
用於管理和處理分組的幻燈片
"""

import os
import json
import shutil
import argparse
from typing import Dict, List, Tuple, Optional
from PIL import Image
import numpy as np


class SlidePostProcessor:
    """幻燈片後處理器"""
    
    def __init__(self, slides_folder: str):
        self.slides_folder = slides_folder
        self.metadata_path = os.path.join(slides_folder, "slides_metadata.json")
        self.metadata = None
        self.load_metadata()
    
    def load_metadata(self):
        """載入元數據"""
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"找不到元數據文件：{self.metadata_path}")
        
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        
        print(f"已載入元數據，共 {len(self.metadata['slides'])} 張幻燈片")
        print(f"分為 {len(self.metadata['groups'])} 組")
    
    def show_summary(self):
        """顯示摘要信息"""
        print("\n=== 幻燈片摘要 ===")
        print(f"視頻來源：{os.path.basename(self.metadata['video_info']['path'])}")
        print(f"視頻時長：{self.metadata['video_info']['duration']:.1f} 秒")
        print(f"總幻燈片數：{len(self.metadata['slides'])}")
        print(f"總組數：{len(self.metadata['groups'])}")
        
        print("\n=== 各組詳情 ===")
        for group_name, group_info in sorted(self.metadata['groups'].items()):
            group_id = int(group_name.split('_')[1])
            slide_count = group_info['slide_count']
            time_range = group_info['time_range']
            
            print(f"\n組 {group_id:02d}: {slide_count} 張幻燈片")
            print(f"  時間範圍: {time_range['start']:.1f}s - {time_range['end']:.1f}s")
            
            if slide_count > 1:
                print(f"  可能是動畫或漸變效果，建議檢查")
    
    def remove_duplicates_in_groups(self, similarity_threshold: float = 0.95):
        """移除組內的重複幻燈片"""
        print(f"\n開始移除組內重複幻燈片（相似度閾值：{similarity_threshold}）...")
        
        removed_count = 0
        
        for group_name, group_info in self.metadata['groups'].items():
            if group_info['slide_count'] <= 1:
                continue
            
            group_id = int(group_name.split('_')[1])
            slides = group_info['slides']
            
            # 標記要刪除的幻燈片
            to_remove = []
            
            for i in range(1, len(slides)):
                prev_slide = slides[i-1]
                curr_slide = slides[i]
                
                # 計算時間差
                time_diff = curr_slide['timestamp'] - prev_slide['timestamp']
                
                # 如果時間差很小，可能是重複捕獲
                if time_diff < 1.0:  # 少於1秒
                    # 比較圖片相似度
                    prev_path = os.path.join(self.slides_folder, prev_slide['filename'])
                    curr_path = os.path.join(self.slides_folder, curr_slide['filename'])
                    
                    if os.path.exists(prev_path) and os.path.exists(curr_path):
                        similarity = self.compare_images(prev_path, curr_path)
                        
                        if similarity > similarity_threshold:
                            to_remove.append(curr_slide['filename'])
                            print(f"  將刪除重複幻燈片：{curr_slide['filename']} (相似度：{similarity:.3f})")
            
            # 刪除標記的文件
            for filename in to_remove:
                filepath = os.path.join(self.slides_folder, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    removed_count += 1
        
        print(f"\n共刪除 {removed_count} 張重複幻燈片")
        
        if removed_count > 0:
            self.update_metadata_after_removal()
    
    def compare_images(self, img1_path: str, img2_path: str) -> float:
        """比較兩張圖片的相似度"""
        try:
            img1 = Image.open(img1_path).convert('RGB')
            img2 = Image.open(img2_path).convert('RGB')
            
            # 調整大小以加快比較
            size = (256, 256)
            img1 = img1.resize(size)
            img2 = img2.resize(size)
            
            # 轉換為 numpy 數組
            arr1 = np.array(img1)
            arr2 = np.array(img2)
            
            # 計算均方誤差
            mse = np.mean((arr1 - arr2) ** 2)
            
            # 轉換為相似度（0-1）
            similarity = 1.0 - (mse / (255.0 ** 2))
            
            return similarity
            
        except Exception as e:
            print(f"比較圖片時出錯：{e}")
            return 0.0
    
    def select_best_from_groups(self, output_folder: str = None):
        """從每組中選擇最佳的幻燈片"""
        if output_folder is None:
            output_folder = os.path.join(self.slides_folder, "selected_slides")
        
        os.makedirs(output_folder, exist_ok=True)
        
        print(f"\n從每組中選擇最佳幻燈片...")
        selected_count = 0
        
        for group_name, group_info in sorted(self.metadata['groups'].items()):
            group_id = int(group_name.split('_')[1])
            slides = group_info['slides']
            
            if not slides:
                continue
            
            # 選擇策略：
            # 1. 如果只有一張，直接選擇
            # 2. 如果有多張，選擇中間的（通常質量較好）
            if len(slides) == 1:
                selected = slides[0]
            else:
                # 選擇中間位置的幻燈片
                middle_idx = len(slides) // 2
                selected = slides[middle_idx]
            
            # 複製選中的幻燈片
            src_path = os.path.join(self.slides_folder, selected['filename'])
            
            # 新文件名：簡化為 slide_001.jpg 格式
            new_filename = f"slide_{group_id:03d}.jpg"
            dst_path = os.path.join(output_folder, new_filename)
            
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                selected_count += 1
                print(f"  組 {group_id:02d}: 選擇 {selected['filename']} -> {new_filename}")
        
        print(f"\n共選擇 {selected_count} 張幻燈片")
        print(f"已保存到：{output_folder}")
        
        # 創建簡化的元數據
        self.create_simplified_metadata(output_folder, selected_count)
    
    def create_simplified_metadata(self, output_folder: str, slide_count: int):
        """創建簡化的元數據"""
        simplified_metadata = {
            "source_video": self.metadata['video_info']['path'],
            "total_slides": slide_count,
            "processing_info": {
                "original_slides": len(self.metadata['slides']),
                "original_groups": len(self.metadata['groups']),
                "selection_method": "best_from_each_group"
            }
        }
        
        metadata_path = os.path.join(output_folder, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(simplified_metadata, f, ensure_ascii=False, indent=2)
    
    def update_metadata_after_removal(self):
        """刪除文件後更新元數據"""
        # 重新掃描文件夾中的文件
        existing_files = set(f for f in os.listdir(self.slides_folder) 
                           if f.endswith('.jpg') and f.startswith('slide_'))
        
        # 更新幻燈片列表
        updated_slides = []
        for slide in self.metadata['slides']:
            if slide['filename'] in existing_files:
                updated_slides.append(slide)
        
        self.metadata['slides'] = updated_slides
        
        # 更新組信息
        for group_name, group_info in self.metadata['groups'].items():
            group_slides = []
            for slide in group_info['slides']:
                if slide['filename'] in existing_files:
                    group_slides.append(slide)
            group_info['slides'] = group_slides
            group_info['slide_count'] = len(group_slides)
        
        # 保存更新後的元數據
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def generate_html_preview(self, output_file: str = None):
        """生成 HTML 預覽頁面"""
        if output_file is None:
            output_file = os.path.join(self.slides_folder, "preview.html")
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>幻燈片預覽</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .group {
            margin-bottom: 30px;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .group-header {
            font-weight: bold;
            margin-bottom: 10px;
            color: #0066cc;
        }
        .slides {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .slide {
            position: relative;
            width: 200px;
        }
        .slide img {
            width: 100%;
            height: 150px;
            object-fit: cover;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .slide-info {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        .highlight {
            background-color: #ffeb3b;
            padding: 2px 4px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h1>幻燈片預覽</h1>
    <p>視頻：{video_name}</p>
    <p>總幻燈片數：{total_slides} | 總組數：{total_groups}</p>
    
"""
        
        video_name = os.path.basename(self.metadata['video_info']['path'])
        html_content = html_content.format(
            video_name=video_name,
            total_slides=len(self.metadata['slides']),
            total_groups=len(self.metadata['groups'])
        )
        
        # 添加每組的預覽
        for group_name, group_info in sorted(self.metadata['groups'].items()):
            group_id = int(group_name.split('_')[1])
            
            html_content += f"""
    <div class="group">
        <div class="group-header">
            組 {group_id:02d} - {group_info['slide_count']} 張幻燈片 
            ({group_info['time_range']['start']:.1f}s - {group_info['time_range']['end']:.1f}s)
        </div>
        <div class="slides">
"""
            
            for slide in group_info['slides']:
                highlight_class = "highlight" if slide['subgroup_idx'] > 1 else ""
                html_content += f"""
            <div class="slide">
                <img src="{slide['filename']}" alt="{slide['filename']}">
                <div class="slide-info {highlight_class}">
                    {slide['filename']}<br>
                    時間: {slide['timestamp']:.1f}s
                </div>
            </div>
"""
            
            html_content += """
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nHTML 預覽已生成：{output_file}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='幻燈片後處理工具')
    parser.add_argument('slides_folder', help='包含幻燈片的文件夾路徑')
    parser.add_argument('--action', choices=['summary', 'remove-duplicates', 'select-best', 'preview'],
                       default='summary', help='要執行的操作')
    parser.add_argument('--output', help='輸出文件夾路徑')
    parser.add_argument('--threshold', type=float, default=0.95,
                       help='相似度閾值（用於去重）')
    
    args = parser.parse_args()
    
    try:
        processor = SlidePostProcessor(args.slides_folder)
        
        if args.action == 'summary':
            processor.show_summary()
        
        elif args.action == 'remove-duplicates':
            processor.remove_duplicates_in_groups(args.threshold)
        
        elif args.action == 'select-best':
            processor.select_best_from_groups(args.output)
        
        elif args.action == 'preview':
            processor.generate_html_preview(args.output)
    
    except Exception as e:
        print(f"錯誤：{e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())