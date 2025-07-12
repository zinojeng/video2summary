#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試進階幻燈片捕獲功能
"""

import os
import sys
import time
from slide_capture_advanced import capture_slides_advanced
from slide_post_processor import SlidePostProcessor


def test_advanced_capture(video_path: str):
    """測試進階捕獲功能"""
    
    if not os.path.exists(video_path):
        print(f"錯誤：找不到視頻文件 {video_path}")
        return
    
    # 設置輸出文件夾
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    output_folder = f"test_advanced_{video_name}_{int(time.time())}"
    
    print("=" * 60)
    print("測試進階幻燈片捕獲功能")
    print("=" * 60)
    print(f"視頻文件: {video_path}")
    print(f"輸出文件夾: {output_folder}")
    print()
    
    # 測試不同的參數組合
    test_configs = [
        {
            "name": "默認設置",
            "similarity_threshold": 0.85,
            "group_threshold": 0.90
        },
        {
            "name": "高敏感度（捕獲更多）",
            "similarity_threshold": 0.75,
            "group_threshold": 0.85
        },
        {
            "name": "低敏感度（捕獲更少）",
            "similarity_threshold": 0.90,
            "group_threshold": 0.95
        }
    ]
    
    # 選擇測試配置
    print("選擇測試配置：")
    for i, config in enumerate(test_configs):
        print(f"{i+1}. {config['name']}")
    
    choice = input("\n請選擇 (1-3，默認為1): ").strip()
    if not choice:
        choice = "1"
    
    try:
        config_idx = int(choice) - 1
        if 0 <= config_idx < len(test_configs):
            config = test_configs[config_idx]
        else:
            config = test_configs[0]
    except:
        config = test_configs[0]
    
    print(f"\n使用配置: {config['name']}")
    print(f"相似度閾值: {config['similarity_threshold']}")
    print(f"分組閾值: {config['group_threshold']}")
    print()
    
    # 執行捕獲
    start_time = time.time()
    success, result = capture_slides_advanced(
        video_path, 
        output_folder,
        config['similarity_threshold'],
        config['group_threshold']
    )
    elapsed_time = time.time() - start_time
    
    if success:
        print("\n" + "=" * 60)
        print("捕獲成功！")
        print(f"耗時: {elapsed_time:.1f} 秒")
        print(f"捕獲幻燈片數: {result['slide_count']}")
        print(f"分組數: {result['group_count']}")
        print(f"輸出文件夾: {result['output_folder']}")
        print(f"元數據文件: {result['metadata_file']}")
        
        # 顯示統計信息
        if 'statistics' in result:
            stats = result['statistics']
            print("\n統計信息:")
            print(f"- 平均每組幻燈片數: {stats['average_slides_per_group']:.1f}")
            print(f"- 各組分布:")
            for group_id, count in sorted(stats['groups_distribution'].items()):
                print(f"  組 {group_id}: {count} 張")
        
        # 詢問是否運行後處理
        print("\n" + "=" * 60)
        print("後處理選項：")
        print("1. 顯示摘要信息")
        print("2. 移除組內重複")
        print("3. 從每組選擇最佳")
        print("4. 生成 HTML 預覽")
        print("5. 跳過後處理")
        
        post_choice = input("\n請選擇 (1-5): ").strip()
        
        if post_choice in ["1", "2", "3", "4"]:
            try:
                processor = SlidePostProcessor(output_folder)
                
                if post_choice == "1":
                    processor.show_summary()
                
                elif post_choice == "2":
                    processor.remove_duplicates_in_groups()
                
                elif post_choice == "3":
                    selected_folder = os.path.join(output_folder, "selected_slides")
                    processor.select_best_from_groups(selected_folder)
                    print(f"\n選擇的幻燈片已保存到: {selected_folder}")
                
                elif post_choice == "4":
                    processor.generate_html_preview()
                    preview_path = os.path.join(output_folder, "preview.html")
                    print(f"\n預覽頁面已生成: {preview_path}")
                    
                    # 嘗試在瀏覽器中打開
                    import webbrowser
                    try:
                        webbrowser.open(f"file://{os.path.abspath(preview_path)}")
                        print("已在瀏覽器中打開預覽頁面")
                    except:
                        print("請手動打開預覽頁面")
                        
            except Exception as e:
                print(f"\n後處理時出錯: {e}")
        
    else:
        print("\n捕獲失敗！")
        print(f"錯誤: {result.get('error', '未知錯誤')}")


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <視頻文件路徑>")
        print()
        print("示例:")
        print(f"  python {sys.argv[0]} /path/to/video.mp4")
        return 1
    
    video_path = sys.argv[1]
    test_advanced_capture(video_path)
    return 0


if __name__ == "__main__":
    exit(main())