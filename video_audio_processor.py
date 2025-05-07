#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
視頻和音頻處理工具

此程序可以處理以下功能：
1. 從 .mp4 文件中提取音頻
2. 捕獲視頻中的幻燈片，並生成 PowerPoint 或 Markdown 文件
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import traceback
import threading
from PIL import Image, ImageTk
import importlib

# 需要時會動態導入的模塊:
# - moviepy (extract_audio_from_video)
# - cv2, numpy, skimage.metrics (capture_slides_from_video)
# - pptx (generate_ppt_from_images)
# - markitdown_helper (custom module for image to markdown conversion)
# - importlib.util (for checking installed modules)

def check_dependencies():
    """檢查必要依賴是否已安裝"""
    import importlib.util
    
    required_packages = [
        "opencv-python", "numpy", "pillow", "moviepy",
        "python-pptx", "scikit-image"
    ]
    
    # 分開檢查 markitdown，因為它可選
    optional_packages = ["markitdown"]
    
    missing_packages = []
    missing_optional = []
    
    for package in required_packages:
        try:
            # 處理特殊套件名稱
            import_name = package.replace("-", "_")
            # 處理 opencv-python 特例
            if package == "opencv-python":
                import_name = "cv2"
            # 處理 python-pptx 特例
            elif package == "python-pptx":
                import_name = "pptx"
            # 處理 pillow 特例
            elif package == "pillow":
                import_name = "PIL"
            # 處理 scikit-image 特例
            elif package == "scikit-image":
                import_name = "skimage"
                
            spec = importlib.util.find_spec(import_name)
            if spec is None:
                missing_packages.append(package)
        except ImportError:
            missing_packages.append(package)
    
    for package in optional_packages:
        try:
            spec = importlib.util.find_spec(package)
            if spec is None:
                missing_optional.append(package)
        except ImportError:
            missing_optional.append(package)
    
    if missing_optional:
        print(f"注意: 未安裝可選套件: {', '.join(missing_optional)}")
        print("如果您想使用 MarkItDown 處理功能，請安裝:")
        print("pip install markitdown>=0.1.1")
    
    return missing_packages


def install_dependencies(packages):
    """安裝缺失的依賴"""
    print(f"正在安裝必要依賴: {', '.join(packages)}")
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + packages
        )
        return True
    except subprocess.CalledProcessError:
        return False


def extract_audio_from_video(video_path, output_path=None, format="mp3"):
    """
    從視頻文件中提取音頻
    
    參數:
        video_path: 視頻文件路徑
        output_path: 輸出音頻文件路徑，默認為原視頻名稱加上音頻格式後綴
        format: 輸出音頻格式，默認為 mp3
        
    返回:
        success: 是否成功
        output_file: 輸出文件路徑或錯誤信息
    """
    try:
        from moviepy import VideoFileClip
        
        # 如果未指定輸出路徑，使用默認路徑
        if not output_path:
            base_name = os.path.splitext(video_path)[0]
            output_path = f"{base_name}.{format}"
            
        # 打開視頻文件
        video_clip = VideoFileClip(video_path)
        
        # 提取音頻
        audio_clip = video_clip.audio
        
        # 寫入音頻文件
        audio_clip.write_audiofile(output_path)
        
        # 釋放資源
        audio_clip.close()
        video_clip.close()
        
        return True, output_path
        
    except Exception as e:
        error_msg = str(e)
        print(f"提取音頻時出錯: {error_msg}")
        return False, error_msg


def capture_slides_from_video(video_path, output_folder=None, similarity_threshold=0.8):
    """
    從視頻文件中捕獲幻燈片
    
    參數:
        video_path: 視頻文件路徑
        output_folder: 輸出幻燈片圖片的文件夾，默認為 video_slides
        similarity_threshold: 圖像相似度閾值，用於檢測幻燈片變化，值越低檢測越敏感
        
    返回:
        success: 是否成功
        result: 包含提取信息的字典或錯誤信息
    """
    try:
        import cv2
        import numpy as np
        from skimage.metrics import structural_similarity as ssim
        
        # 如果未指定輸出文件夾，使用默認文件夾
        if not output_folder:
            # 使用視頻文件名作為文件夾名
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_folder = f"video_slides_{video_name}"
        
        # 確保輸出文件夾存在
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
        # 打開視頻文件
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return False, "無法打開視頻文件"
            
        # 獲取視頻信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        # 計算採樣間隔（秒）
        # 每秒檢查一次幀，可以根據需要調整
        sample_interval = 1
        
        # 初始化幀計數器和上一幀
        frame_idx = 0
        prev_frame = None
        saved_count = 0
        last_saved_time = -1000  # 上次保存的時間點，初始為負值

        while True:
            # 設置當前幀位置
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            
            # 讀取當前幀
            ret, frame = cap.read()
            
            if not ret:
                break
                
            # 計算當前時間點（秒）
            current_time = frame_idx / fps
            
            # 轉換為灰度圖像用於相似度比較
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 如果是第一幀或與上一幀相比相似度低於閾值，則保存
            if prev_frame is None or (
                current_time - last_saved_time >= 2.0 and  # 確保至少間隔2秒
                ssim(prev_frame, gray_frame) < similarity_threshold
            ):
                # 保存當前幀
                output_path = os.path.join(
                    output_folder, f"slide_{saved_count:03d}.png"
                )
                cv2.imwrite(output_path, frame)
                saved_count += 1
                last_saved_time = current_time
                
                # 更新上一幀
                prev_frame = gray_frame
                
                print(f"保存幻燈片 {saved_count} 於 {current_time:.2f} 秒")
            
            # 更新幀索引，跳過一些幀以提高效率
            frame_idx += int(fps * sample_interval)
            
            # 檢查是否已到達視頻結尾
            if frame_idx >= frame_count:
                break
                
        # 釋放資源
        cap.release()
        
        return True, {
            "output_folder": output_folder,
            "slide_count": saved_count,
            "video_duration": duration
        }
        
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return False, error_msg


def generate_ppt_from_images(image_folder, output_file=None, title="視頻捕獲的幻燈片"):
    """
    將圖片文件夾轉換為 PowerPoint 文件
    
    參數:
        image_folder: 包含幻燈片圖片的文件夾
        output_file: 輸出的 PowerPoint 文件路徑，默認為文件夾名+.pptx
        title: 演示文稿標題
        
    返回:
        success: 是否成功
        output_file: 輸出文件路徑或錯誤信息
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches
        
        # 如果未指定輸出文件，使用默認文件
        if not output_file:
            output_file = os.path.join(
                os.path.dirname(image_folder), 
                f"{os.path.basename(image_folder)}.pptx"
            )
            
        # 創建新的 PowerPoint 演示文稿
        prs = Presentation()
        
        # 獲取幻燈片尺寸
        slide_width = prs.slide_width
        slide_height = prs.slide_height
        
        # 獲取所有圖片文件
        image_files = []
        for filename in sorted(os.listdir(image_folder)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(image_folder, filename))
                
        if not image_files:
            return False, "未找到圖片文件"
            
        # 添加標題幻燈片
        title_slide_layout = prs.slide_layouts[0]  # 標題布局
        title_slide = prs.slides.add_slide(title_slide_layout)
        title_slide.shapes.title.text = title
        if hasattr(title_slide.placeholders, 'subtitle'):
            title_slide.placeholders[1].text = f"包含 {len(image_files)} 張幻燈片"
            
        # 為每張圖片創建一個幻燈片
        blank_slide_layout = prs.slide_layouts[6]  # 空白布局
        
        for img_path in image_files:
            slide = prs.slides.add_slide(blank_slide_layout)
            
            # 添加圖片
            left = top = Inches(0)
            img = slide.shapes.add_picture(
                img_path, left, top, width=slide_width, height=slide_height
            )
            
        # 保存演示文稿
        prs.save(output_file)
        
        return True, output_file
        
    except Exception as e:
        error_msg = str(e)
        print(f"生成 PowerPoint 時出錯: {error_msg}")
        traceback.print_exc()
        return False, error_msg


def generate_markdown_from_images(image_folder, output_file=None, title="視頻捕獲的幻燈片", use_markitdown=True, api_key=None):
    """
    將圖片文件夾轉換為 Markdown 文件
    
    參數:
        image_folder: 包含幻燈片圖片的文件夾
        output_file: 輸出的 Markdown 文件路徑，默認為文件夾名+.md
        title: Markdown 文件標題
        use_markitdown: 是否使用 MarkItDown 庫進行圖片文本提取
        api_key: 如果使用 MarkItDown 並需要 LLM 支持，提供 API Key
        
    返回:
        success: 是否成功
        output_file: 輸出文件路徑或錯誤信息
    """
    try:
        # 如果未指定輸出文件，使用默認文件
        if not output_file:
            output_file = os.path.join(
                os.path.dirname(image_folder), 
                f"{os.path.basename(image_folder)}.md"
            )
            
        # 獲取所有圖片文件
        image_files = []
        for filename in sorted(os.listdir(image_folder)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(image_folder, filename))
                
        if not image_files:
            return False, "未找到圖片文件"
        
        # 嘗試使用我們的自定義 markitdown_helper
        try:
            import markitdown_helper
            
            print(f"使用自定義 markitdown_helper 處理 {len(image_files)} 張圖片...")
            success, result, info = markitdown_helper.convert_images_to_markdown(
                image_paths=image_files,
                output_file=output_file,
                title=title,
                use_llm=(api_key is not None),
                api_key=api_key
            )
            
            if success:
                return True, result
            else:
                print(f"使用 markitdown_helper 失敗: {info.get('error', '未知錯誤')}")
                # 繼續使用基本方法
        except ImportError:
            print("找不到 markitdown_helper 模組，繼續嘗試其他方法...")
        except Exception as e:
            print(f"使用 markitdown_helper 時出錯: {e}")
            traceback.print_exc()
            
        # 如果使用 MarkItDown，則調用相應函數
        if use_markitdown:
            try:
                # 檢查 markitdown 是否已安裝
                import importlib.util
                markitdown_spec = importlib.util.find_spec("markitdown")
                
                if markitdown_spec is not None:
                    import markitdown
                    
                    # 使用 markitdown 庫
                    print(f"使用 MarkItDown 庫處理 {len(image_files)} 張圖片...")
                    
                    # 創建 MarkItDown 實例
                    converter = markitdown.MarkItDown()
                    
                    # 添加自訂標題的 Markdown 內容
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"# {title}\n\n")
                        
                        for i, img_path in enumerate(image_files):
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
                            
                            try:
                                # 使用 markitdown 分析圖片內容
                                result = converter.convert(img_path)
                                if result and result.text_content:
                                    f.write(f"{result.text_content.strip()}\n\n")
                            except Exception as img_err:
                                print(f"分析圖片 {img_path} 時出錯: {img_err}")
                            
                            f.write("---\n\n")
                    
                    print(f"已成功生成 Markdown 文件: {output_file}")
                    return True, output_file
                else:
                    print("找不到 markitdown 模組，將使用基本方法生成 Markdown")
                    use_markitdown = False
                    
            except ImportError as e:
                print(f"MarkItDown 庫導入錯誤: {e}")
                print("將使用基本方法生成 Markdown")
                use_markitdown = False
            except Exception as e:
                print(f"使用 MarkItDown 時出錯: {e}")
                print("將使用基本方法生成 Markdown")
                traceback.print_exc()
                use_markitdown = False
        
        # 使用基本方法生成 Markdown
        print("使用基本方法生成 Markdown...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            
            for i, img_path in enumerate(image_files):
                # 獲取相對路徑，使 Markdown 中的圖片鏈接更短
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
        
        return True, output_file
        
    except Exception as e:
        error_msg = str(e)
        print(f"生成 Markdown 時出錯: {error_msg}")
        traceback.print_exc()
        return False, error_msg


class VideoAudioProcessor:
    """視頻和音頻處理應用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("視頻和音頻處理工具")
        self.root.geometry("900x700")
        
        # 保存使用者的 API Key
        self.saved_api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # 創建頁面框架
        self.setup_ui()
    
    def setup_ui(self):
        """設置使用者介面"""
        # 建立選項卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 第一個選項卡：音頻提取
        self.audio_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.audio_frame, text="音頻提取")
        
        # 第二個選項卡：幻燈片捕獲
        self.slide_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.slide_frame, text="幻燈片捕獲")
        
        # 第三個選項卡：幻燈片處理
        self.process_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.process_frame, text="幻燈片處理")
        
        # 設置音頻提取 UI
        self.setup_audio_ui()
        
        # 設置幻燈片捕獲 UI
        self.setup_slide_ui()
        
        # 設置幻燈片處理 UI
        self.setup_process_ui()
    
    def setup_audio_ui(self):
        """設置音頻提取界面"""
        frame = self.audio_frame
        
        # 頂部說明文字
        info_label = tk.Label(
            frame, 
            text="此功能可以從視頻文件中提取音頻軌道",
            font=("Arial", 12)
        )
        info_label.pack(pady=20)
        
        # 視頻文件選擇區域
        video_frame = tk.Frame(frame)
        video_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(video_frame, text="視頻文件:").pack(side=tk.LEFT, padx=10)
        self.video_entry = tk.Entry(video_frame, width=50)
        self.video_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.video_browse_btn = tk.Button(
            video_frame, text="瀏覽...", 
            command=lambda: self.browse_file(
                self.video_entry, 
                filetypes=[("視頻文件", "*.mp4 *.avi *.mkv *.mov")]
            )
        )
        self.video_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出音頻設置區域
        output_frame = tk.Frame(frame)
        output_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(output_frame, text="輸出文件:").pack(side=tk.LEFT, padx=10)
        self.audio_output_entry = tk.Entry(output_frame, width=50)
        self.audio_output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.audio_browse_btn = tk.Button(
            output_frame, text="瀏覽...", 
            command=lambda: self.save_file(
                self.audio_output_entry, 
                filetypes=[("音頻文件", "*.mp3 *.wav *.aac")]
            )
        )
        self.audio_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 音頻格式選擇
        format_frame = tk.Frame(frame)
        format_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(format_frame, text="音頻格式:").pack(side=tk.LEFT, padx=10)
        
        self.audio_format_var = tk.StringVar(value="mp3")
        
        tk.Radiobutton(
            format_frame, text="MP3", 
            variable=self.audio_format_var, value="mp3"
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            format_frame, text="WAV", 
            variable=self.audio_format_var, value="wav"
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            format_frame, text="AAC", 
            variable=self.audio_format_var, value="aac"
        ).pack(side=tk.LEFT, padx=5)
        
        # 狀態顯示
        self.audio_status_var = tk.StringVar(value="準備就緒")
        status_label = tk.Label(
            frame, textvariable=self.audio_status_var,
            font=("Arial", 10), fg="blue"
        )
        status_label.pack(pady=10)
        
        # 進度條
        self.audio_progress = ttk.Progressbar(
            frame, orient="horizontal", length=300, mode="indeterminate"
        )
        self.audio_progress.pack(pady=10)
        
        # 提取按鈕
        self.extract_btn = tk.Button(
            frame, text="提取音頻", command=self.extract_audio,
            bg="#4CAF50", fg="white", height=2, width=20
        )
        self.extract_btn.pack(pady=20)
    
    def browse_file(self, entry_widget, filetypes):
        """瀏覽並選擇文件"""
        file_path = filedialog.askopenfilename(
            initialdir=".",
            title="選擇文件",
            filetypes=filetypes
        )
        if file_path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, file_path)
            
            # 如果是視頻文件，自動生成音頻輸出路徑
            if entry_widget == self.video_entry:
                base_name = os.path.splitext(file_path)[0]
                audio_format = self.audio_format_var.get()
                output_path = f"{base_name}.{audio_format}"
                
                self.audio_output_entry.delete(0, tk.END)
                self.audio_output_entry.insert(0, output_path)
    
    def save_file(self, entry_widget, filetypes):
        """選擇保存文件的路徑"""
        file_path = filedialog.asksaveasfilename(
            initialdir=".",
            title="保存文件",
            filetypes=filetypes
        )
        if file_path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, file_path)
    
    def extract_audio(self):
        """提取音頻按鈕點擊處理"""
        video_path = self.video_entry.get()
        output_path = self.audio_output_entry.get()
        audio_format = self.audio_format_var.get()
        
        if not video_path:
            messagebox.showwarning("警告", "請選擇視頻文件")
            return
            
        # 確保輸出路徑有正確的擴展名
        if output_path and not output_path.lower().endswith(f".{audio_format}"):
            output_path = f"{os.path.splitext(output_path)[0]}.{audio_format}"
            self.audio_output_entry.delete(0, tk.END)
            self.audio_output_entry.insert(0, output_path)
        
        # 開始提取（在背景線程中運行）
        self.audio_status_var.set("正在提取音頻...")
        self.audio_progress.start(10)
        self.extract_btn.config(state=tk.DISABLED)
        
        def extract_thread():
            success, result = extract_audio_from_video(
                video_path, output_path, audio_format
            )
            
            # 在主線程中更新 UI
            self.root.after(0, lambda: self.extraction_completed(success, result))
        
        threading.Thread(target=extract_thread).start()
    
    def extraction_completed(self, success, result):
        """音頻提取完成後的處理"""
        self.audio_progress.stop()
        self.extract_btn.config(state=tk.NORMAL)
        
        if success:
            self.audio_status_var.set(f"提取完成: {result}")
            messagebox.showinfo("成功", f"音頻已成功提取到: {result}")
        else:
            self.audio_status_var.set(f"提取失敗: {result}")
            messagebox.showerror("錯誤", f"音頻提取失敗: {result}")
            
    def setup_slide_ui(self):
        """設置幻燈片捕獲界面"""
        frame = self.slide_frame
        
        # 頂部說明文字
        info_label = tk.Label(
            frame, 
            text="此功能可從視頻文件中捕獲幻燈片，並將其保存為圖片",
            font=("Arial", 12)
        )
        info_label.pack(pady=20)
        
        # 視頻文件選擇區域
        video_frame = tk.Frame(frame)
        video_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(video_frame, text="視頻文件:").pack(side=tk.LEFT, padx=10)
        self.slide_video_entry = tk.Entry(video_frame, width=50)
        self.slide_video_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.slide_video_browse_btn = tk.Button(
            video_frame, text="瀏覽...", 
            command=lambda: self.browse_file(
                self.slide_video_entry, 
                filetypes=[("視頻文件", "*.mp4 *.avi *.mkv *.mov")]
            )
        )
        self.slide_video_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出文件夾設置區域
        output_frame = tk.Frame(frame)
        output_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(output_frame, text="輸出文件夾:").pack(side=tk.LEFT, padx=10)
        self.slide_output_entry = tk.Entry(output_frame, width=50)
        self.slide_output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.slide_browse_btn = tk.Button(
            output_frame, text="瀏覽...", 
            command=self.browse_slide_folder
        )
        self.slide_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 相似度閾值設置
        threshold_frame = tk.Frame(frame)
        threshold_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(threshold_frame, text="相似度閾值:").pack(side=tk.LEFT, padx=10)
        
        self.threshold_var = tk.DoubleVar(value=0.8)
        self.threshold_scale = ttk.Scale(
            threshold_frame, from_=0.5, to=0.95, 
            variable=self.threshold_var, 
            length=200,
            orient=tk.HORIZONTAL
        )
        self.threshold_scale.pack(side=tk.LEFT, padx=5)
        
        # 顯示當前閾值
        self.threshold_label = tk.Label(
            threshold_frame, 
            textvariable=tk.StringVar(value="0.80")
        )
        self.threshold_label.pack(side=tk.LEFT, padx=5)
        
        # 更新閾值顯示
        def update_threshold_label(*args):
            value = self.threshold_var.get()
            self.threshold_label.config(text=f"{value:.2f}")
            
        self.threshold_var.trace_add("write", update_threshold_label)
        
        # 說明文字
        tk.Label(
            threshold_frame, 
            text="（值越低檢測越敏感，可能會捕獲較多幻燈片）"
        ).pack(side=tk.LEFT, padx=10)
        
        # 狀態顯示
        self.slide_status_var = tk.StringVar(value="準備就緒")
        status_label = tk.Label(
            frame, textvariable=self.slide_status_var,
            font=("Arial", 10), fg="blue"
        )
        status_label.pack(pady=10)
        
        # 進度條
        self.slide_progress = ttk.Progressbar(
            frame, orient="horizontal", length=300, mode="indeterminate"
        )
        self.slide_progress.pack(pady=10)
        
        # 捕獲按鈕
        self.capture_btn = tk.Button(
            frame, text="捕獲幻燈片", command=self.capture_slides,
            bg="#2196F3", fg="white", height=2, width=20
        )
        self.capture_btn.pack(pady=20)
        
    def browse_slide_folder(self):
        """瀏覽並選擇幻燈片輸出文件夾"""
        folder_path = filedialog.askdirectory(
            initialdir=".",
            title="選擇保存幻燈片的文件夾"
        )
        if folder_path:
            self.slide_output_entry.delete(0, tk.END)
            self.slide_output_entry.insert(0, folder_path)
    
    def capture_slides(self):
        """捕獲幻燈片按鈕點擊處理"""
        video_path = self.slide_video_entry.get()
        output_folder = self.slide_output_entry.get()
        threshold = self.threshold_var.get()
        
        if not video_path:
            messagebox.showwarning("警告", "請選擇視頻文件")
            return
            
        # 如果未指定輸出文件夾，根據視頻名稱創建
        if not output_folder:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_folder = f"video_slides_{video_name}"
            
            self.slide_output_entry.delete(0, tk.END)
            self.slide_output_entry.insert(0, output_folder)
        
        # 開始捕獲（在背景線程中運行）
        self.slide_status_var.set("正在捕獲幻燈片...")
        self.slide_progress.start(10)
        self.capture_btn.config(state=tk.DISABLED)
        
        def capture_thread():
            success, result = capture_slides_from_video(
                video_path, output_folder, threshold
            )
            
            # 在主線程中更新 UI
            self.root.after(0, lambda: self.capture_completed(success, result))
        
        threading.Thread(target=capture_thread).start()
    
    def capture_completed(self, success, result):
        """幻燈片捕獲完成後的處理"""
        self.slide_progress.stop()
        self.capture_btn.config(state=tk.NORMAL)
        
        if success:
            output_folder = result.get("output_folder", "未知文件夾")
            slide_count = result.get("slide_count", 0)
            
            self.slide_status_var.set(f"捕獲完成: {slide_count} 張幻燈片")
            
            # 同時更新處理標籤頁的文件夾路徑
            self.process_folder_entry.delete(0, tk.END)
            self.process_folder_entry.insert(0, output_folder)
            
            # 詢問是否切換到處理標籤頁
            if messagebox.askyesno(
                "成功", 
                f"已成功捕獲 {slide_count} 張幻燈片到文件夾: {output_folder}\n"
                f"是否立即處理這些幻燈片？"
            ):
                self.notebook.select(2)  # 切換到處理標籤頁
        else:
            self.slide_status_var.set(f"捕獲失敗: {result}")
            messagebox.showerror("錯誤", f"幻燈片捕獲失敗: {result}")

    def setup_process_ui(self):
        """設置幻燈片處理界面"""
        frame = self.process_frame
        
        # 頂部說明文字
        info_label = tk.Label(
            frame, 
            text="此功能可將捕獲的幻燈片轉換為 PowerPoint 或 Markdown",
            font=("Arial", 12)
        )
        info_label.pack(pady=20)
        
        # 幻燈片文件夾選擇區域
        folder_frame = tk.Frame(frame)
        folder_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(folder_frame, text="幻燈片文件夾:").pack(side=tk.LEFT, padx=10)
        self.process_folder_entry = tk.Entry(folder_frame, width=50)
        self.process_folder_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.process_browse_btn = tk.Button(
            folder_frame, text="瀏覽...", 
            command=self.browse_process_folder
        )
        self.process_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出格式選擇
        format_frame = tk.Frame(frame)
        format_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(format_frame, text="輸出格式:").pack(side=tk.LEFT, padx=10)
        
        self.output_format_var = tk.StringVar(value="both")
        
        tk.Radiobutton(
            format_frame, text="僅 PowerPoint", 
            variable=self.output_format_var, value="pptx"
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            format_frame, text="僅 Markdown", 
            variable=self.output_format_var, value="markdown"
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            format_frame, text="兩者都要", 
            variable=self.output_format_var, value="both"
        ).pack(side=tk.LEFT, padx=5)
        
        # Markdown 處理選項
        md_frame = tk.Frame(frame)
        md_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(md_frame, text="Markdown 處理:").pack(side=tk.LEFT, padx=10)
        
        self.md_process_var = tk.StringVar(value="basic")
        
        tk.Radiobutton(
            md_frame, text="基本處理", 
            variable=self.md_process_var, value="basic"
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(
            md_frame, text="使用 MarkItDown (推薦)", 
            variable=self.md_process_var, value="markitdown"
        ).pack(side=tk.LEFT, padx=5)
        
        # API Key 設置
        api_frame = tk.Frame(frame)
        api_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(api_frame, text="OpenAI API Key:").pack(side=tk.LEFT, padx=10)
        self.api_key_entry = tk.Entry(api_frame, width=50)
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 從環境變數獲取 API Key
        api_key_env = os.environ.get("OPENAI_API_KEY", "")
        if api_key_env:
            self.api_key_entry.insert(0, api_key_env)
            
        # 提示文字
        tip_label = tk.Label(
            frame, 
            text="注意: 使用 MarkItDown 可以更好地提取幻燈片中的文字，但需要安裝 markitdown 套件",
            font=("Arial", 10), fg="gray"
        )
        tip_label.pack(pady=5)
        
        # 標題設置
        title_frame = tk.Frame(frame)
        title_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(title_frame, text="文檔標題:").pack(side=tk.LEFT, padx=10)
        self.title_entry = tk.Entry(title_frame, width=50)
        self.title_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.title_entry.insert(0, "視頻捕獲的幻燈片")
        
        # 狀態顯示
        self.process_status_var = tk.StringVar(value="準備就緒")
        status_label = tk.Label(
            frame, textvariable=self.process_status_var,
            font=("Arial", 10), fg="blue"
        )
        status_label.pack(pady=10)
        
        # 進度條
        self.process_progress = ttk.Progressbar(
            frame, orient="horizontal", length=300, mode="indeterminate"
        )
        self.process_progress.pack(pady=10)
        
        # 處理按鈕
        self.process_btn = tk.Button(
            frame, text="處理幻燈片", command=self.process_slides,
            bg="#4CAF50", fg="white", height=2, width=20
        )
        self.process_btn.pack(pady=20)
    
    def browse_process_folder(self):
        """瀏覽並選擇幻燈片處理的源文件夾"""
        folder_path = filedialog.askdirectory(
            initialdir=".",
            title="選擇包含幻燈片的文件夾"
        )
        if folder_path:
            self.process_folder_entry.delete(0, tk.END)
            self.process_folder_entry.insert(0, folder_path)
    
    def process_slides(self):
        """處理幻燈片按鈕點擊處理"""
        folder = self.process_folder_entry.get()
        output_format = self.output_format_var.get()
        md_process = self.md_process_var.get()
        api_key = self.api_key_entry.get()
        title = self.title_entry.get()
        
        if not folder:
            messagebox.showwarning("警告", "請選擇幻燈片文件夾")
            return
        
        if not os.path.exists(folder):
            messagebox.showerror("錯誤", f"文件夾不存在: {folder}")
            return
            
        # 確保選擇的是目錄而不是文件
        if not os.path.isdir(folder):
            messagebox.showerror("錯誤", f"選擇的路徑不是目錄: {folder}")
            return
            
        # 檢查文件夾中是否有圖片
        has_images = False
        for filename in os.listdir(folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                has_images = True
                break
                
        if not has_images:
            messagebox.showwarning("警告", "選定的文件夾中未找到圖片")
            return
            
        # 開始處理（在背景線程中運行）
        self.process_status_var.set("正在處理幻燈片...")
        self.process_progress.start(10)
        self.process_btn.config(state=tk.DISABLED)
        
        def process_thread():
            # 處理結果
            results = []
            success = True
            
            # 根據選擇處理 PowerPoint
            if output_format in ["pptx", "both"]:
                ppt_success, ppt_result = generate_ppt_from_images(
                    folder, None, title
                )
                success = success and ppt_success
                if ppt_success:
                    results.append(f"PPT: {ppt_result}")
                else:
                    results.append(f"PPT 失敗: {ppt_result}")
            
            # 根據選擇處理 Markdown
            if output_format in ["markdown", "both"]:
                use_markitdown = (md_process == "markitdown")
                md_success, md_result = generate_markdown_from_images(
                    folder, None, title, use_markitdown, api_key
                )
                success = success and md_success
                if md_success:
                    results.append(f"Markdown: {md_result}")
                else:
                    results.append(f"Markdown 失敗: {md_result}")
            
            # 在主線程中更新 UI
            self.root.after(0, lambda: self.processing_completed(success, results))
        
        threading.Thread(target=process_thread).start()
    
    def processing_completed(self, success, results):
        """幻燈片處理完成後的處理"""
        self.process_progress.stop()
        self.process_btn.config(state=tk.NORMAL)
        
        if success:
            self.process_status_var.set("處理完成")
            
            # 顯示處理結果
            result_text = "\n".join(results)
            messagebox.showinfo("成功", f"幻燈片處理完成:\n{result_text}")
        else:
            self.process_status_var.set("處理失敗")
            
            # 顯示處理結果
            result_text = "\n".join(results)
            messagebox.showerror("錯誤", f"幻燈片處理失敗:\n{result_text}")


def main():
    """主函數"""
    # 檢查依賴
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"缺少以下依賴: {', '.join(missing_packages)}")
        choice = input("是否自動安裝這些依賴？(y/n): ")
        
        if choice.lower() == 'y':
            if not install_dependencies(missing_packages):
                print("依賴安裝失敗，請手動執行：")
                print(f"pip install {' '.join(missing_packages)}")
                sys.exit(1)
        else:
            print("請手動安裝以下依賴後再運行:")
            print(f"pip install {' '.join(missing_packages)}")
            sys.exit(1)
    
    try:
        # 創建並運行應用
        root = tk.Tk()
        app = VideoAudioProcessor(root)
        
        # 顯示使用提示
        messagebox.showinfo(
            "歡迎使用", 
            "歡迎使用視頻和音頻處理工具\n\n"
            "本工具提供以下功能：\n"
            "1. 從視頻文件中提取音頻\n"
            "2. 從視頻文件中捕獲幻燈片\n"
            "3. 將捕獲的幻燈片轉換為 PowerPoint 或 Markdown\n\n"
            "請選擇相應的標籤頁開始使用"
        )
        
        root.mainloop()
        
    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"啟動失敗: {str(e)}\n{error_msg}")
        messagebox.showerror("啟動錯誤", f"程序啟動失敗:\n{str(e)}")


if __name__ == "__main__":
    main() 