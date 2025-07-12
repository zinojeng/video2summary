#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量幻燈片內容分析工具 - Gemini 版本
使用 Google Gemini AI 分析所有幻燈片文件夾中的圖片內容
"""

import os
import sys
import argparse
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# 導入 Gemini 版本的 markitdown 輔助模組
from markitdown_helper_gemini import convert_images_to_markdown_gemini


class BatchSlidesAnalyzer:
    """批量幻燈片分析器 - Gemini 版本"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp",
                 selected_only: bool = False, force: bool = False,
                 skip_existing: bool = True, auto_confirm: bool = False):
        """
        初始化分析器
        
        參數:
            api_key: Google API Key
            model: 使用的模型
            selected_only: 是否只處理 selected_slides 子文件夾
            force: 是否強制重新處理已有分析的文件夾
            skip_existing: 是否跳過已存在分析文件的文件夾
            auto_confirm: 是否自動確認處理
        """
        self.api_key = api_key
        self.model = model
        self.selected_only = selected_only
        self.force = force
        self.skip_existing = skip_existing and not force
        self.auto_confirm = auto_confirm
        
        self.processed_folders = []
        self.failed_folders = []
        self.skipped_folders = []
        
        self.stats = {
            'total_folders': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_images': 0,
            'processing_time': 0,
            'api_calls': 0
        }
    
    def find_slide_folders(self, base_path: str) -> List[str]:
        """
        查找所有幻燈片文件夾
        
        參數:
            base_path: 基礎搜索路徑
            
        返回:
            幻燈片文件夾路徑列表
        """
        slide_folders = []
        
        try:
            # 使用 pathlib 遞歸搜索
            base_path_obj = Path(base_path)
            
            # 查找所有以 _slides 結尾的文件夾
            for folder in base_path_obj.rglob('*_slides'):
                # 排除 selected_slides 子文件夾
                if folder.name == 'selected_slides':
                    continue
                
                # 確保是目錄
                if folder.is_dir():
                    slide_folders.append(str(folder))
            
            # 排序以保持一致性
            slide_folders = sorted(slide_folders)
            
        except Exception as e:
            print(f"搜索幻燈片文件夾時出錯: {e}")
        
        return slide_folders
    
    def should_process_folder(self, folder_path: str) -> Tuple[bool, str]:
        """
        檢查是否應該處理該文件夾
        
        返回:
            (should_process, reason)
        """
        if not self.skip_existing:
            return True, "force mode"
        
        # 檢查分析文件是否已存在
        if self.selected_only:
            selected_path = os.path.join(folder_path, 'selected_slides')
            if os.path.exists(selected_path):
                analysis_file = os.path.join(folder_path, 'selected_slides_analysis_gemini.md')
                if os.path.exists(analysis_file):
                    return False, "selected_slides_analysis_gemini.md already exists"
        else:
            analysis_file = os.path.join(folder_path, 'slides_analysis_gemini.md')
            if os.path.exists(analysis_file):
                return False, "slides_analysis_gemini.md already exists"
        
        return True, "needs processing"
    
    def analyze_folder(self, folder_path: str) -> Dict:
        """
        分析單個幻燈片文件夾
        
        返回:
            處理結果字典
        """
        result = {
            'folder': folder_path,
            'status': 'pending',
            'images_processed': 0,
            'output_files': [],
            'error': None,
            'processing_time': 0
        }
        
        start_time = time.time()
        
        try:
            folder_name = os.path.basename(folder_path)
            parent_dir = os.path.basename(os.path.dirname(folder_path))
            
            print(f"\n{'='*60}")
            print(f"處理文件夾: {parent_dir}/{folder_name}")
            print(f"{'='*60}")
            
            # 決定要處理的圖片路徑
            if self.selected_only:
                # 只處理 selected_slides 子文件夾
                selected_path = os.path.join(folder_path, 'selected_slides')
                if not os.path.exists(selected_path):
                    result['status'] = 'skipped'
                    result['error'] = 'No selected_slides subfolder'
                    print("未找到 selected_slides 子文件夾，跳過")
                    return result
                
                # 獲取 selected_slides 中的圖片
                image_files = []
                for f in sorted(os.listdir(selected_path)):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
                        image_files.append(os.path.join(selected_path, f))
                
                output_file = os.path.join(folder_path, 'selected_slides_analysis_gemini.md')
                title = f"{parent_dir} - 精選幻燈片分析 (Gemini)"
                
            else:
                # 處理主文件夾中的所有圖片
                image_files = []
                for f in sorted(os.listdir(folder_path)):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
                        image_files.append(os.path.join(folder_path, f))
                
                output_file = os.path.join(folder_path, 'slides_analysis_gemini.md')
                title = f"{parent_dir} - 完整幻燈片分析 (Gemini)"
            
            if not image_files:
                result['status'] = 'skipped'
                result['error'] = 'No image files found'
                print("未找到圖片文件，跳過")
                return result
            
            print(f"找到 {len(image_files)} 張圖片")
            print(f"使用模型: {self.model}")
            print(f"開始分析...")
            
            # 調用 Gemini 版本的 markitdown_helper 進行分析
            success, output_path, info = convert_images_to_markdown_gemini(
                image_paths=image_files,
                output_file=output_file,
                title=title,
                use_llm=True,
                api_key=self.api_key,
                model=self.model
            )
            
            if success:
                result['status'] = 'success'
                result['images_processed'] = info.get('processed_images', 0)
                result['output_files'].append(output_path)
                self.stats['total_images'] += result['images_processed']
                self.stats['api_calls'] += result['images_processed']
                
                print(f"✅ 分析完成！")
                print(f"   處理圖片數: {result['images_processed']}")
                print(f"   輸出文件: {os.path.basename(output_path)}")
                
                # 如果不是只處理 selected，也處理 selected_slides
                if not self.selected_only and os.path.exists(os.path.join(folder_path, 'selected_slides')):
                    print(f"\n同時處理 selected_slides 子文件夾...")
                    
                    selected_path = os.path.join(folder_path, 'selected_slides')
                    selected_images = []
                    for f in sorted(os.listdir(selected_path)):
                        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
                            selected_images.append(os.path.join(selected_path, f))
                    
                    if selected_images:
                        selected_output = os.path.join(folder_path, 'selected_slides_analysis_gemini.md')
                        selected_title = f"{parent_dir} - 精選幻燈片分析 (Gemini)"
                        
                        success2, output_path2, info2 = convert_images_to_markdown_gemini(
                            image_paths=selected_images,
                            output_file=selected_output,
                            title=selected_title,
                            use_llm=True,
                            api_key=self.api_key,
                            model=self.model
                        )
                        
                        if success2:
                            result['output_files'].append(output_path2)
                            result['images_processed'] += info2.get('processed_images', 0)
                            self.stats['total_images'] += info2.get('processed_images', 0)
                            self.stats['api_calls'] += info2.get('processed_images', 0)
                            print(f"   精選幻燈片分析完成: {info2.get('processed_images', 0)} 張")
                
            else:
                result['status'] = 'failed'
                result['error'] = info.get('error', 'Unknown error')
                print(f"❌ 分析失敗: {result['error']}")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            print(f"❌ 處理時出錯: {str(e)}")
        
        result['processing_time'] = time.time() - start_time
        return result
    
    def process_all(self, base_path: str):
        """
        處理所有幻燈片文件夾
        """
        print("\n🔍 批量幻燈片內容分析工具 - Gemini 版本")
        print("="*60)
        
        # 查找所有幻燈片文件夾
        print(f"\n搜索幻燈片文件夾...")
        slide_folders = self.find_slide_folders(base_path)
        
        if not slide_folders:
            print("未找到幻燈片文件夾")
            return
        
        self.stats['total_folders'] = len(slide_folders)
        print(f"找到 {len(slide_folders)} 個幻燈片文件夾")
        
        # 檢查哪些需要處理
        folders_to_process = []
        folders_to_skip = []
        
        for folder in slide_folders:
            should_process, reason = self.should_process_folder(folder)
            if should_process:
                folders_to_process.append(folder)
            else:
                folders_to_skip.append((folder, reason))
                self.skipped_folders.append(folder)
        
        print(f"\n需要處理: {len(folders_to_process)} 個")
        print(f"將跳過: {len(folders_to_skip)} 個")
        
        if folders_to_skip and not self.force:
            print("\n將跳過的文件夾:")
            for folder, reason in folders_to_skip[:5]:  # 只顯示前5個
                print(f"  - {os.path.basename(folder)} ({reason})")
            if len(folders_to_skip) > 5:
                print(f"  ... 還有 {len(folders_to_skip) - 5} 個")
        
        if not folders_to_process:
            print("\n沒有需要處理的文件夾")
            return
        
        # 確認處理
        print(f"\n預計 API 調用次數: 約 {len(folders_to_process) * 30} 次")
        print(f"使用模型: {self.model}")
        
        if len(folders_to_process) > 1 and not self.auto_confirm:
            confirm = input(f"\n確定要處理這 {len(folders_to_process)} 個文件夾嗎？(y/n): ")
            if confirm.lower() != 'y':
                print("已取消")
                return
        
        # 開始批量處理
        start_time = time.time()
        
        for i, folder_path in enumerate(folders_to_process, 1):
            print(f"\n進度: {i}/{len(folders_to_process)} ({i/len(folders_to_process)*100:.1f}%)")
            
            result = self.analyze_folder(folder_path)
            
            if result['status'] == 'success':
                self.processed_folders.append(result)
                self.stats['processed'] += 1
            elif result['status'] == 'failed':
                self.failed_folders.append(result)
                self.stats['failed'] += 1
            else:
                self.stats['skipped'] += 1
            
            # 顯示即時進度
            elapsed = time.time() - start_time
            if i < len(folders_to_process):
                avg_time_per_folder = elapsed / i
                remaining_folders = len(folders_to_process) - i
                eta = avg_time_per_folder * remaining_folders
                print(f"\n⏱️  已用時: {elapsed:.1f}秒, 預計剩餘: {eta:.1f}秒")
        
        self.stats['processing_time'] = time.time() - start_time
        self.stats['skipped'] += len(folders_to_skip)
        
        # 顯示總結
        self.show_summary()
    
    def show_summary(self):
        """顯示處理總結"""
        print("\n" + "="*60)
        print("📊 處理總結")
        print("="*60)
        
        print(f"\n總體統計:")
        print(f"  總文件夾數: {self.stats['total_folders']}")
        print(f"  成功處理: {self.stats['processed']}")
        print(f"  處理失敗: {self.stats['failed']}")
        print(f"  已跳過: {self.stats['skipped']}")
        print(f"  總圖片數: {self.stats['total_images']}")
        print(f"  API 調用次數: {self.stats['api_calls']}")
        print(f"  總耗時: {self.stats['processing_time']:.1f} 秒 ({self.stats['processing_time']/60:.1f} 分鐘)")
        
        if self.stats['processed'] > 0:
            avg_time = self.stats['processing_time'] / self.stats['processed']
            avg_images = self.stats['total_images'] / self.stats['processed']
            print(f"  平均每文件夾耗時: {avg_time:.1f} 秒")
            print(f"  平均每文件夾圖片數: {avg_images:.1f}")
        
        if self.processed_folders:
            print(f"\n✅ 成功處理的文件夾:")
            for result in self.processed_folders[:10]:  # 只顯示前10個
                folder_name = os.path.basename(result['folder'])
                parent_name = os.path.basename(os.path.dirname(result['folder']))
                print(f"  - {parent_name}/{folder_name}")
                print(f"    圖片數: {result['images_processed']}")
                for output in result['output_files']:
                    print(f"    輸出: {os.path.basename(output)}")
            
            if len(self.processed_folders) > 10:
                print(f"  ... 還有 {len(self.processed_folders) - 10} 個")
        
        if self.failed_folders:
            print(f"\n❌ 處理失敗的文件夾:")
            for result in self.failed_folders:
                folder_name = os.path.basename(result['folder'])
                print(f"  - {folder_name}")
                print(f"    錯誤: {result['error']}")
        
        # 保存處理報告
        self.save_report()
    
    def save_report(self):
        """保存處理報告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'model': self.model,
                'stats': self.stats,
                'processed': [
                    {
                        'folder': r['folder'],
                        'images': r['images_processed'],
                        'outputs': r['output_files'],
                        'time': r['processing_time']
                    }
                    for r in self.processed_folders
                ],
                'failed': [
                    {
                        'folder': r['folder'],
                        'error': r['error']
                    }
                    for r in self.failed_folders
                ],
                'skipped': self.skipped_folders
            }
            
            report_file = f"batch_analysis_gemini_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 處理報告已保存: {report_file}")
            
        except Exception as e:
            print(f"\n保存報告時出錯: {e}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='批量分析幻燈片內容 - Gemini 版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 分析所有幻燈片文件夾
  %(prog)s /path/to/ADA2025 --api-key YOUR_API_KEY
  
  # 只分析精選幻燈片
  %(prog)s /path/to/ADA2025 --api-key YOUR_API_KEY --selected-only
  
  # 使用其他 Gemini 模型
  %(prog)s /path/to/ADA2025 --api-key YOUR_API_KEY --model gemini-1.5-pro
  
  # 強制重新處理
  %(prog)s /path/to/ADA2025 --api-key YOUR_API_KEY --force
  
  # 自動確認處理
  %(prog)s /path/to/ADA2025 --api-key YOUR_API_KEY --yes
"""
    )
    
    parser.add_argument('path', help='包含幻燈片文件夾的路徑')
    parser.add_argument('-k', '--api-key', required=True,
                       help='Google API Key')
    parser.add_argument('-m', '--model', default='gemini-2.0-flash-exp',
                       help='使用的 Gemini 模型 (默認: gemini-2.0-flash-exp)')
    parser.add_argument('-s', '--selected-only', action='store_true',
                       help='只處理 selected_slides 子文件夾')
    parser.add_argument('-f', '--force', action='store_true',
                       help='強制重新處理（即使已有分析文件）')
    parser.add_argument('-y', '--yes', action='store_true',
                       help='自動確認處理，不詢問')
    
    args = parser.parse_args()
    
    # 檢查路徑
    if not os.path.exists(args.path):
        print(f"錯誤：路徑不存在: {args.path}")
        sys.exit(1)
    
    # 創建分析器
    analyzer = BatchSlidesAnalyzer(
        api_key=args.api_key,
        model=args.model,
        selected_only=args.selected_only,
        force=args.force,
        auto_confirm=args.yes
    )
    
    # 開始處理
    try:
        analyzer.process_all(args.path)
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷處理")
        analyzer.show_summary()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()