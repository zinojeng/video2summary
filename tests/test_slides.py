#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
幻燈片處理功能測試腳本
"""

import os
import sys

# 測試使用 markitdown_helper 模組處理圖片
def test_image_processing():
    print("開始測試幻燈片處理功能")
    
    try:
        # 導入 markitdown_helper 模組
        import markitdown_helper
        print("成功導入 markitdown_helper 模組")
        
        # 設置測試路徑
        test_dir = "test_slides"
        os.makedirs(test_dir, exist_ok=True)
        
        # 創建一些測試圖片
        create_test_images(test_dir)
        
        # 使用 markitdown_helper 將圖片轉換為 Markdown
        print("測試將圖片轉換為 Markdown")
        success, md_file, info = markitdown_helper.convert_images_to_markdown(
            image_paths=[
                os.path.join(test_dir, f"slide_{i}.png") 
                for i in range(1, 4)
            ],
            output_file=os.path.join(test_dir, "slides.md"),
            title="測試幻燈片"
        )
        
        if success:
            print(f"成功生成 Markdown 文件: {md_file}")
            print(f"處理信息: {info}")
        else:
            print(f"生成 Markdown 失敗: {info.get('error', '未知錯誤')}")
        
        # 使用 markitdown_helper 將圖片轉換為 PowerPoint
        print("測試將圖片轉換為 PowerPoint")
        success = markitdown_helper.process_images_to_ppt(
            image_dir=test_dir,
            output_ppt=os.path.join(test_dir, "slides.pptx"),
            title="測試幻燈片"
        )
        
        if success:
            print(f"成功生成 PowerPoint 文件")
        else:
            print(f"生成 PowerPoint 失敗")
        
        return True
        
    except Exception as e:
        print(f"測試過程中出錯: {e}")
        import traceback
        traceback.print_exc()
        return False


# 創建一些測試圖片
def create_test_images(output_dir):
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        for i in range(1, 4):
            img = Image.new('RGB', (800, 600), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # 繪製幻燈片編號
            draw.rectangle([(0, 0), (800, 100)], fill=(200, 200, 255))
            
            # 嘗試加載字體，如果失敗則使用默認字體
            try:
                font = ImageFont.truetype("Arial", 60)
            except:
                font = ImageFont.load_default()
                
            draw.text(
                (400, 50),
                f"幻燈片 {i}",
                fill=(0, 0, 128),
                font=font,
                anchor="mm"
            )
            
            # 繪製一些內容
            draw.text(
                (400, 300),
                f"這是第 {i} 張幻燈片的內容",
                fill=(0, 0, 0),
                font=font,
                anchor="mm"
            )
            
            # 保存圖片
            img.save(os.path.join(output_dir, f"slide_{i}.png"))
            
        print(f"已創建 3 張測試幻燈片在 {output_dir} 目錄")
            
    except Exception as e:
        print(f"創建測試圖片時出錯: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if test_image_processing():
        print("測試完成")
    else:
        print("測試失敗") 