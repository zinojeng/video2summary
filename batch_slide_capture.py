#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量視頻幻燈片捕獲工具
支持處理單個視頻或整個文件夾中的視頻
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict, Tuple
import json

# 導入我們的捕獲模組
from slide_capture_advanced import capture_slides_advanced
from slide_post_processor import SlidePostProcessor


class BatchSlideCapture:
    """批量幻燈片捕獲類"""
    
    def __init__(self, similarity_threshold: float = 0.80, 
                 group_threshold: float = 0.88,
                 auto_select: bool = False,
                 recursive: bool = False,
                 force: bool = False,
                 list_only: bool = False,
                 yes: bool = False):
        self.similarity_threshold = similarity_threshold
        self.group_threshold = group_threshold
        self.auto_select = auto_select
        self.recursive = recursive
        self.force = force
        self.list_only = list_only
        self.yes = yes
        self.video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        self.processed_videos = []
        self.failed_videos = []
        self.stats = {
            'total_videos': 0,
            'processed': 0,
            'failed': 0,
            'total_slides': 0,
            'total_groups': 0,
            'processing_time': 0
        }
    
    def find_videos(self, path: str) -> List[str]:
        """查找視頻文件"""
        video_files = []
        path_obj = Path(path)
        
        if path_obj.is_file():
            # 單個文件
            if path_obj.suffix.lower() in self.video_extensions and not path_obj.name.startswith('._'):
                video_files.append(str(path_obj))
            else:
                print(f"警告：{path} 不是支持的視頻格式或是系統文件")
        elif path_obj.is_dir():
            # 目錄
            if self.recursive:
                # 遞歸搜索
                for ext in self.video_extensions:
                    for p in path_obj.rglob(f'*{ext}'):
                        # 過濾掉 macOS 資源分支文件
                        if not p.name.startswith('._'):
                            video_files.append(str(p))
            else:
                # 只搜索當前目錄
                for ext in self.video_extensions:
                    for p in path_obj.glob(f'*{ext}'):
                        # 過濾掉 macOS 資源分支文件
                        if not p.name.startswith('._'):
                            video_files.append(str(p))
        else:
            print(f"錯誤：{path} 不存在")
        
        # 排序並去重
        video_files = sorted(list(set(video_files)))
        return video_files
    
    def process_video(self, video_path: str) -> Dict:
        """處理單個視頻"""
        print(f"\n{'='*60}")
        print(f"處理視頻: {os.path.basename(video_path)}")
        print(f"路徑: {video_path}")
        print(f"{'='*60}")
        
        # 確定輸出文件夾
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_folder = os.path.join(video_dir, f"{video_name}_slides")
        
        # 檢查是否已經處理過（檢查多種可能的文件夾名稱）
        if not self.force:
            possible_slide_folders = [
                f"{video_name}_slides",
                f"{video_name}_slide",
                "slides",
                "slide",
                "Slides",
                "Slide"
            ]
            
            for folder_name in possible_slide_folders:
                folder_path = os.path.join(video_dir, folder_name)
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    # 檢查文件夾中是否有圖片文件
                    try:
                        files = os.listdir(folder_path)
                        has_images = any(f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) 
                                       for f in files if not f.startswith('._'))
                        
                        if has_images:
                            print(f"⚠️  已存在幻燈片文件夾 '{folder_name}'，跳過處理")
                            return {
                                'status': 'skipped',
                                'video': video_path,
                                'output': folder_path,
                                'reason': 'already_processed',
                                'existing_folder': folder_name
                            }
                    except Exception:
                        # 如果無法讀取文件夾內容，繼續檢查其他文件夾
                        pass
        
        # 開始計時
        start_time = time.time()
        
        try:
            # 使用進階模式捕獲幻燈片
            print(f"使用進階模式捕獲幻燈片...")
            print(f"相似度閾值: {self.similarity_threshold}")
            print(f"分組閾值: {self.group_threshold}")
            
            success, result = capture_slides_advanced(
                video_path, 
                output_folder,
                self.similarity_threshold,
                self.group_threshold
            )
            
            if success:
                elapsed_time = time.time() - start_time
                
                # 更新統計
                self.stats['total_slides'] += result['slide_count']
                self.stats['total_groups'] += result['group_count']
                
                print(f"\n✅ 捕獲成功！")
                print(f"   幻燈片數: {result['slide_count']}")
                print(f"   分組數: {result['group_count']}")
                print(f"   耗時: {elapsed_time:.1f} 秒")
                print(f"   輸出: {output_folder}")
                
                # 如果啟用自動選擇
                if self.auto_select and result['slide_count'] > 0:
                    print(f"\n自動選擇每組最佳幻燈片...")
                    try:
                        processor = SlidePostProcessor(output_folder)
                        selected_folder = os.path.join(output_folder, "selected_slides")
                        processor.select_best_from_groups(selected_folder)
                        print(f"   已選擇最佳幻燈片到: selected_slides/")
                    except Exception as e:
                        print(f"   選擇最佳幻燈片時出錯: {e}")
                
                # 生成 HTML 預覽
                print(f"\n生成 HTML 預覽...")
                try:
                    self._create_simple_preview(output_folder)
                    print(f"   預覽已生成: preview.html")
                except Exception as e:
                    print(f"   生成預覽時出錯: {e}")
                
                return {
                    'status': 'success',
                    'video': video_path,
                    'output': output_folder,
                    'slide_count': result['slide_count'],
                    'group_count': result['group_count'],
                    'processing_time': elapsed_time
                }
            else:
                print(f"\n❌ 捕獲失敗: {result.get('error', '未知錯誤')}")
                return {
                    'status': 'failed',
                    'video': video_path,
                    'error': result.get('error', '未知錯誤')
                }
                
        except Exception as e:
            print(f"\n❌ 處理時出錯: {str(e)}")
            return {
                'status': 'failed',
                'video': video_path,
                'error': str(e)
            }
    
    def _create_simple_preview(self, slides_folder: str):
        """創建簡單的 HTML 預覽（內部方法）"""
        # 載入元數據
        metadata_path = os.path.join(slides_folder, "slides_metadata.json")
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 生成 HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>幻燈片預覽 - {os.path.basename(slides_folder)}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .info {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .group {{
            margin-bottom: 30px;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .group-header {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #0066cc;
        }}
        .slides {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .slide {{
            position: relative;
            width: 200px;
        }}
        .slide img {{
            width: 100%;
            height: 150px;
            object-fit: cover;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .slide-info {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .highlight {{
            background-color: #ffeb3b;
            padding: 2px 4px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <h1>幻燈片預覽</h1>
    
    <div class="info">
        <p><strong>視頻：</strong>{os.path.basename(metadata['video_info']['path'])}</p>
        <p><strong>時長：</strong>{metadata['video_info']['duration']:.1f} 秒</p>
        <p><strong>總幻燈片數：</strong>{len(metadata['slides'])}</p>
        <p><strong>總組數：</strong>{len(metadata['groups'])}</p>
    </div>
"""
        
        # 添加每組預覽
        for group_name in sorted(metadata['groups'].keys(), key=lambda x: int(x.split('_')[1])):
            group_info = metadata['groups'][group_name]
            group_id = int(group_name.split('_')[1])
            
            html += f"""
    <div class="group">
        <div class="group-header">
            組 {group_id:02d} - {group_info['slide_count']} 張幻燈片 
            ({group_info['time_range']['start']:.1f}s - {group_info['time_range']['end']:.1f}s)
        </div>
        <div class="slides">
"""
            
            for slide in group_info['slides']:
                highlight_class = "highlight" if slide['subgroup_idx'] > 1 else ""
                html += f"""
            <div class="slide">
                <img src="{slide['filename']}" alt="{slide['filename']}">
                <div class="slide-info {highlight_class}">
                    {slide['filename']}<br>
                    時間: {slide['timestamp']:.1f}s
                </div>
            </div>
"""
            
            html += """
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        # 保存文件
        output_path = os.path.join(slides_folder, "preview.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def process_batch(self, path: str):
        """批量處理視頻"""
        print("\n🎬 批量視頻幻燈片捕獲工具")
        print("="*60)
        
        # 查找視頻文件
        print(f"\n搜尋視頻文件...")
        video_files = self.find_videos(path)
        
        if not video_files:
            print("未找到視頻文件")
            return
        
        self.stats['total_videos'] = len(video_files)
        
        print(f"找到 {len(video_files)} 個視頻文件:")
        
        # 預先檢查哪些視頻需要處理
        videos_to_process = []
        videos_to_skip = []
        
        for video in video_files:
            # 快速檢查是否已處理
            video_dir = os.path.dirname(video)
            video_name = os.path.splitext(os.path.basename(video))[0]
            
            skip = False
            if not self.force:
                for folder_name in [f"{video_name}_slides", f"{video_name}_slide", "slides", "slide", "Slides", "Slide"]:
                    folder_path = os.path.join(video_dir, folder_name)
                    if os.path.exists(folder_path) and os.path.isdir(folder_path):
                        try:
                            files = os.listdir(folder_path)
                            if any(f.lower().endswith(('.jpg', '.jpeg', '.png')) for f in files if not f.startswith('._')):
                                videos_to_skip.append((video, folder_name))
                                skip = True
                                break
                        except:
                            pass
            
            if not skip:
                videos_to_process.append(video)
        
        # 顯示狀態
        print(f"\n需要處理: {len(videos_to_process)} 個")
        print(f"將跳過: {len(videos_to_skip)} 個（已有幻燈片）")
        
        if videos_to_process:
            print("\n將處理的視頻:")
            for i, video in enumerate(videos_to_process, 1):
                print(f"  {i}. {os.path.basename(video)}")
        
        if videos_to_skip:
            print("\n將跳過的視頻（已有幻燈片）:")
            for video, folder in videos_to_skip:
                print(f"  - {os.path.basename(video)} (已有 '{folder}' 文件夾)")
        
        # 如果是 list-only 模式，到此為止
        if self.list_only:
            print("\n(僅列表模式，不執行處理)")
            return
        
        # 確認處理
        if videos_to_process and len(videos_to_process) > 1 and not self.yes:
            confirm = input(f"\n確定要處理這 {len(videos_to_process)} 個視頻嗎？(y/n): ")
            if confirm.lower() != 'y':
                print("已取消")
                return
        elif not videos_to_process:
            print("\n沒有需要處理的視頻")
            return
        
        # 開始批量處理
        start_time = time.time()
        
        for i, video_path in enumerate(video_files, 1):
            print(f"\n進度: {i}/{len(video_files)}")
            
            result = self.process_video(video_path)
            
            if result['status'] == 'success':
                self.processed_videos.append(result)
                self.stats['processed'] += 1
            elif result['status'] == 'failed':
                self.failed_videos.append(result)
                self.stats['failed'] += 1
        
        self.stats['processing_time'] = time.time() - start_time
        
        # 顯示總結
        self.show_summary()
    
    def show_summary(self):
        """顯示處理總結"""
        print("\n" + "="*60)
        print("📊 處理總結")
        print("="*60)
        
        print(f"\n總體統計:")
        print(f"  總視頻數: {self.stats['total_videos']}")
        print(f"  成功處理: {self.stats['processed']}")
        print(f"  處理失敗: {self.stats['failed']}")
        print(f"  已跳過: {self.stats['total_videos'] - self.stats['processed'] - self.stats['failed']}")
        print(f"  總幻燈片數: {self.stats['total_slides']}")
        print(f"  總組數: {self.stats['total_groups']}")
        print(f"  總耗時: {self.stats['processing_time']:.1f} 秒")
        
        if self.stats['processed'] > 0:
            avg_time = self.stats['processing_time'] / self.stats['processed']
            avg_slides = self.stats['total_slides'] / self.stats['processed']
            print(f"  平均每視頻耗時: {avg_time:.1f} 秒")
            print(f"  平均每視頻幻燈片數: {avg_slides:.1f}")
        
        if self.processed_videos:
            print(f"\n✅ 成功處理的視頻:")
            for result in self.processed_videos:
                print(f"  - {os.path.basename(result['video'])}")
                print(f"    幻燈片: {result['slide_count']} | 分組: {result['group_count']}")
                print(f"    輸出: {result['output']}")
        
        if self.failed_videos:
            print(f"\n❌ 處理失敗的視頻:")
            for result in self.failed_videos:
                print(f"  - {os.path.basename(result['video'])}")
                print(f"    錯誤: {result['error']}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='批量視頻幻燈片捕獲工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 處理單個視頻
  %(prog)s /path/to/video.mp4
  
  # 處理整個文件夾（非遞歸）
  %(prog)s /path/to/folder
  
  # 遞歸處理文件夾中的所有視頻
  %(prog)s /path/to/folder --recursive
  
  # 自定義閾值並自動選擇最佳幻燈片
  %(prog)s /path/to/folder --threshold 0.85 --group-threshold 0.90 --auto-select
"""
    )
    
    parser.add_argument('path', help='視頻文件或文件夾路徑')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='遞歸搜索子文件夾中的視頻')
    parser.add_argument('-t', '--threshold', type=float, default=0.80,
                       help='相似度閾值 (默認: 0.80)')
    parser.add_argument('-g', '--group-threshold', type=float, default=0.88,
                       help='分組閾值 (默認: 0.88)')
    parser.add_argument('-a', '--auto-select', action='store_true',
                       help='自動選擇每組最佳幻燈片')
    parser.add_argument('-f', '--force', action='store_true',
                       help='強制重新處理（即使已有幻燈片文件夾）')
    parser.add_argument('-l', '--list-only', action='store_true',
                       help='僅列出將要處理的視頻，不執行處理')
    parser.add_argument('-y', '--yes', action='store_true',
                       help='自動確認處理，跳過用戶確認提示')
    
    args = parser.parse_args()
    
    # 創建批量處理器
    processor = BatchSlideCapture(
        similarity_threshold=args.threshold,
        group_threshold=args.group_threshold,
        auto_select=args.auto_select,
        recursive=args.recursive,
        force=args.force,
        list_only=args.list_only,
        yes=args.yes
    )
    
    # 開始處理
    try:
        processor.process_batch(args.path)
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷處理")
        processor.show_summary()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()