#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MarkItDown 輔助工具 - Gemini 版本
提供從圖片轉換到 Markdown 的功能，支持 Google Gemini API
"""

import os
import base64
import traceback
from typing import List, Tuple, Dict, Any, Optional
import time


def convert_images_to_markdown_gemini(
    image_paths: List[str],
    output_file: str,
    title: str = "圖片內容分析",
    use_llm: bool = False,
    api_key: Optional[str] = None,
    model: str = "gemini-2.0-flash-exp"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    將圖片文件轉換為 Markdown 文件（使用 Gemini API）
    
    參數:
        image_paths: 圖片文件路徑列表
        output_file: 輸出的 Markdown 文件路徑
        title: Markdown 文件標題
        use_llm: 是否使用 LLM 進行圖片文字識別與分析
        api_key: Google API Key
        model: 使用的 Gemini 模型
        
    返回:
        success: 是否成功
        output_file: 輸出文件路徑
        info: 包含轉換統計信息的字典
    """
    try:
        # 過濾掉 macOS 的隱藏文件和非圖片文件
        valid_image_paths = []
        skipped_files = []
        supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        
        for img_path in image_paths:
            basename = os.path.basename(img_path)
            # 跳過以 ._ 開頭的 macOS 隱藏文件
            if basename.startswith('._'):
                skipped_files.append(img_path)
                print(f"跳過 macOS 隱藏文件: {basename}")
                continue
            
            # 檢查文件擴展名
            ext = os.path.splitext(basename)[1].lower()
            if ext not in supported_formats:
                skipped_files.append(img_path)
                print(f"跳過不支持的文件格式: {basename}")
                continue
                
            valid_image_paths.append(img_path)
        
        if not valid_image_paths:
            return False, "", {
                "error": "沒有有效的圖片文件可處理",
                "skipped_files": skipped_files,
                "success": False
            }
        
        info = {
            "success": True, 
            "processed_images": len(valid_image_paths),
            "skipped_files": len(skipped_files),
            "total_files": len(image_paths)
        }
        
        # 如果需要使用 LLM 進行圖片識別和分析
        if use_llm and api_key:
            try:
                import google.generativeai as genai
                
                # 設置 API Key
                genai.configure(api_key=api_key)
                
                # 創建模型實例
                gemini_model = genai.GenerativeModel(model)
                
                print(f"使用 {model} 模型分析 {len(valid_image_paths)} 張圖片...")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {title}\n\n")
                    
                    for i, img_path in enumerate(valid_image_paths):
                        # 添加標題和圖片
                        slide_num = i + 1
                        f.write(f"## 幻燈片 {slide_num}\n\n")
                        
                        # 獲取相對路徑
                        try:
                            rel_path = os.path.relpath(
                                img_path, 
                                os.path.dirname(output_file)
                            )
                        except Exception:
                            rel_path = img_path
                            
                        f.write(f"![幻燈片 {slide_num}]({rel_path})\n\n")
                        
                        # 使用 Gemini 視覺模型分析圖片
                        print(
                            f"分析圖片 {slide_num}/{len(valid_image_paths)}: "
                            f"{os.path.basename(img_path)}"
                        )
                        
                        try:
                            # 讀取圖片
                            import PIL.Image
                            image = PIL.Image.open(img_path)
                            
                            # 準備提示詞
                            prompt = (
                                "請仔細分析這張幻燈片圖片，並完成以下任務：\n"
                                "1. 識別並提取圖片中所有可見的文本內容\n"
                                "2. 描述圖片中的圖表、表格和其他視覺元素\n"
                                "3. 以結構化的Markdown格式返回內容\n"
                                "4. 保持原始的格式和層次結構\n"
                                "5. 如果有表格，請使用Markdown表格格式\n"
                                "6. 如果有列表，請使用Markdown列表格式\n\n"
                                "請直接返回分析結果，不需要額外的說明。"
                            )
                            
                            # 生成內容
                            response = gemini_model.generate_content([prompt, image])
                            
                            # 寫入分析結果
                            if response.text:
                                f.write(f"{response.text}\n\n")
                            else:
                                f.write("*無法分析此圖片的內容*\n\n")
                            
                            f.write("---\n\n")
                            
                            # 添加延遲以避免速率限制 (Gemini限制: 10請求/分鐘)
                            # 每處理一張圖片等待7秒，確保不超過速率限制
                            # 10請求/分鐘 = 1請求/6秒，加上緩衝時間
                            time.sleep(7)
                            
                        except Exception as e:
                            error_msg = str(e)
                            print(f"分析圖片 {img_path} 時出錯: {error_msg}")
                            f.write(f"*分析圖片時出錯: {error_msg}*\n\n")
                            f.write("---\n\n")
                
                info["llm_used"] = True
                info["model"] = model
                return True, output_file, info
                
            except ImportError:
                print("Google Generative AI 模組未安裝，請執行: pip install google-generativeai pillow")
                info["error"] = "Missing google-generativeai module"
                info["llm_used"] = False
                # 繼續使用基本方法
            except Exception as e:
                print(f"使用 Gemini 分析圖片時出錯: {str(e)}")
                traceback.print_exc()
                info["error"] = str(e)
                info["llm_used"] = False
                # 繼續使用基本方法
        
        # 使用基本方法生成 Markdown
        print("使用基本方法生成 Markdown...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            
            for i, img_path in enumerate(valid_image_paths):
                # 獲取相對路徑
                try:
                    rel_path = os.path.relpath(
                        img_path, 
                        os.path.dirname(output_file)
                    )
                except Exception:
                    rel_path = img_path
                    
                # 添加幻燈片標題和圖片
                slide_num = i + 1
                f.write(f"## 幻燈片 {slide_num}\n\n")
                f.write(f"![幻燈片 {slide_num}]({rel_path})\n\n")
                f.write("---\n\n")
        
        info["llm_used"] = False
        return True, output_file, info
        
    except Exception as e:
        error_msg = str(e)
        print(f"生成 Markdown 時出錯: {error_msg}")
        traceback.print_exc()
        return False, "", {"error": error_msg, "success": False}