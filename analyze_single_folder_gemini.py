#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
單個文件夾幻燈片分析工具 - Gemini 版本
"""

import os
import sys
import argparse
from markitdown_helper_gemini import convert_images_to_markdown_gemini


def main():
    parser = argparse.ArgumentParser(
        description='分析單個幻燈片文件夾',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('folder', help='幻燈片文件夾路徑')
    parser.add_argument('-k', '--api-key', required=True, help='Google API Key')
    parser.add_argument('-m', '--model', default='gemini-2.0-flash-exp',
                       help='使用的 Gemini 模型')
    parser.add_argument('-s', '--selected-only', action='store_true',
                       help='只處理 selected_slides 子文件夾')
    
    args = parser.parse_args()
    
    # 檢查文件夾
    if not os.path.exists(args.folder):
        print(f"錯誤：文件夾不存在: {args.folder}")
        sys.exit(1)
    
    folder_name = os.path.basename(args.folder)
    parent_dir = os.path.basename(os.path.dirname(args.folder))
    
    print(f"\n分析文件夾: {parent_dir}/{folder_name}")
    print("="*60)
    
    # 決定要處理的圖片
    if args.selected_only:
        selected_path = os.path.join(args.folder, 'selected_slides')
        if not os.path.exists(selected_path):
            print("錯誤：未找到 selected_slides 子文件夾")
            sys.exit(1)
        
        image_files = []
        for f in sorted(os.listdir(selected_path)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
                image_files.append(os.path.join(selected_path, f))
        
        output_file = os.path.join(args.folder, 'selected_slides_analysis_gemini.md')
        title = f"{parent_dir} - 精選幻燈片分析 (Gemini)"
    else:
        image_files = []
        for f in sorted(os.listdir(args.folder)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith('._'):
                image_files.append(os.path.join(args.folder, f))
        
        output_file = os.path.join(args.folder, 'slides_analysis_gemini.md')
        title = f"{parent_dir} - 完整幻燈片分析 (Gemini)"
    
    if not image_files:
        print("錯誤：未找到圖片文件")
        sys.exit(1)
    
    print(f"找到 {len(image_files)} 張圖片")
    print(f"使用模型: {args.model}")
    print(f"預計處理時間: {len(image_files) * 6} 秒 ({len(image_files) * 6 / 60:.1f} 分鐘)")
    print(f"開始分析...\n")
    
    # 分析
    success, output_path, info = convert_images_to_markdown_gemini(
        image_paths=image_files,
        output_file=output_file,
        title=title,
        use_llm=True,
        api_key=args.api_key,
        model=args.model
    )
    
    if success:
        print(f"\n✅ 分析完成！")
        print(f"處理圖片數: {info.get('processed_images', 0)}")
        print(f"輸出文件: {output_path}")
    else:
        print(f"\n❌ 分析失敗: {info.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()