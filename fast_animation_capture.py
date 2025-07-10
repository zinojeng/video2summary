#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速動畫捕獲模組
專門快速檢測和捕獲幻燈片的動畫變化
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict
import os
import time
from skimage.metrics import structural_similarity as ssim


class FastAnimationCapture:
    """快速動畫捕獲類"""
    
    def __init__(self, video_path: str, output_folder: str, threshold: float = 0.85):
        self.video_path = video_path
        self.output_folder = output_folder
        self.threshold = threshold
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # 動畫檢測參數
        self.min_animation_interval = 1.0  # 最小動畫間隔（秒）
        self.max_animation_interval = 15.0  # 最大動畫間隔（秒）
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def quick_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """快速計算兩張圖片的差異"""
        # 縮小到更小的尺寸以加快速度
        small1 = cv2.resize(img1, (160, 120))
        small2 = cv2.resize(img2, (160, 120))
        
        # 轉為灰度
        gray1 = cv2.cvtColor(small1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(small2, cv2.COLOR_BGR2GRAY)
        
        # 計算均方誤差
        mse = np.mean((gray1 - gray2) ** 2)
        return 1.0 - (mse / 255.0 / 255.0)  # 歸一化為相似度
    
    def detect_content_change(self, img1: np.ndarray, img2: np.ndarray) -> Tuple[bool, float]:
        """檢測內容變化（針對動畫優化）"""
        # 將圖片分成9宮格
        h, w = img1.shape[:2]
        grid_h, grid_w = h // 3, w // 3
        
        changes = []
        
        for i in range(3):
            for j in range(3):
                # 提取區域
                y1, y2 = i * grid_h, (i + 1) * grid_h
                x1, x2 = j * grid_w, (j + 1) * grid_w
                
                region1 = img1[y1:y2, x1:x2]
                region2 = img2[y1:y2, x1:x2]
                
                # 計算區域差異
                diff = cv2.absdiff(region1, region2)
                change_ratio = np.sum(diff > 30) / diff.size
                changes.append(change_ratio)
        
        # 如果有1-3個區域發生變化，可能是動畫
        significant_changes = sum(1 for c in changes if c > 0.01)
        is_animation = 1 <= significant_changes <= 4
        avg_change = np.mean(changes)
        
        return is_animation, avg_change
    
    def fast_capture(self) -> Tuple[bool, Dict]:
        """快速捕獲方法"""
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            
            print(f"快速動畫檢測：{os.path.basename(self.video_path)}")
            print(f"總時長：{self.total_frames/self.fps:.1f}秒")
            
            # 第一步：快速掃描找出主要幻燈片
            print("\n第一步：快速識別主要幻燈片...")
            main_slides = self.find_main_slides()
            
            # 第二步：檢測每張幻燈片的動畫變化
            print(f"\n第二步：檢測 {len(main_slides)} 張幻燈片的動畫效果...")
            all_frames = self.detect_animations(main_slides)
            
            # 保存結果
            print(f"\n保存 {len(all_frames)} 張圖片...")
            saved_files = self.save_frames(all_frames)
            
            return True, {
                "output_folder": self.output_folder,
                "slide_count": len(saved_files),
                "saved_files": saved_files,
                "main_slides": len(main_slides),
                "total_frames": self.total_frames
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, {"error": str(e)}
    
    def find_main_slides(self) -> List[Tuple[int, np.ndarray]]:
        """快速找出主要幻燈片（跳過相似幀）"""
        main_slides = []
        prev_frame = None
        
        # 使用較大的步長快速掃描
        step = max(int(self.fps * 2), 30)  # 每2秒或30幀檢查一次
        
        for i in range(0, self.total_frames, step):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            if prev_frame is None:
                main_slides.append((i, frame.copy()))
                prev_frame = frame
            else:
                # 快速檢查相似度
                similarity = self.quick_diff(prev_frame, frame)
                
                if similarity < self.threshold:
                    # 不同的幻燈片
                    main_slides.append((i, frame.copy()))
                    prev_frame = frame
            
            # 顯示進度
            if i % (step * 10) == 0:
                print(f"掃描進度：{i/self.total_frames*100:.1f}%")
        
        print(f"找到 {len(main_slides)} 張主要幻燈片")
        return main_slides
    
    def detect_animations(self, main_slides: List[Tuple[int, np.ndarray]]) -> List[Tuple[int, np.ndarray, str]]:
        """檢測每張幻燈片的動畫變化"""
        all_frames = []
        
        for slide_idx, (frame_idx, slide_frame) in enumerate(main_slides):
            slide_num = slide_idx + 1
            
            # 添加主幻燈片
            all_frames.append((frame_idx, slide_frame, f"slide_{slide_num:03d}"))
            
            # 確定搜索範圍
            start_idx = frame_idx
            if slide_idx < len(main_slides) - 1:
                end_idx = main_slides[slide_idx + 1][0]
            else:
                end_idx = min(frame_idx + int(self.fps * 60), self.total_frames)  # 最多搜索60秒
            
            # 在範圍內尋找動畫變化
            animation_frames = self.find_animations_in_range(
                slide_frame, start_idx, end_idx, slide_num
            )
            
            all_frames.extend(animation_frames)
            
            print(f"幻燈片 {slide_num}: 找到 {len(animation_frames)} 個動畫狀態")
        
        return all_frames
    
    def find_animations_in_range(self, base_frame: np.ndarray, start_idx: int, end_idx: int, slide_num: int) -> List[Tuple[int, np.ndarray, str]]:
        """在指定範圍內尋找動畫變化"""
        animation_frames = []
        animation_count = 1
        
        # 使用較小的步長檢查動畫
        step = max(int(self.fps * 0.5), 5)  # 每0.5秒或5幀檢查一次
        
        prev_animation_frame = base_frame
        last_animation_idx = start_idx
        
        for i in range(start_idx + step, end_idx, step):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            # 檢查與基礎幻燈片的相似度
            base_similarity = self.quick_diff(base_frame, frame)
            
            # 如果與基礎幻燈片差異太大，可能是新幻燈片
            if base_similarity < 0.7:
                break
            
            # 檢查是否有動畫變化
            is_animation, change_ratio = self.detect_content_change(prev_animation_frame, frame)
            
            # 時間間隔
            time_gap = (i - last_animation_idx) / self.fps
            
            if is_animation and time_gap >= self.min_animation_interval:
                animation_count += 1
                animation_frames.append((
                    i, 
                    frame.copy(), 
                    f"slide_{slide_num:03d}_{animation_count}"
                ))
                prev_animation_frame = frame
                last_animation_idx = i
        
        return animation_frames
    
    def save_frames(self, frames: List[Tuple[int, np.ndarray, str]]) -> List[str]:
        """保存所有幀"""
        saved_files = []
        
        for frame_idx, frame, name_prefix in frames:
            timestamp = frame_idx / self.fps
            filename = f"{name_prefix}_t{timestamp:.1f}s.jpg"
            filepath = os.path.join(self.output_folder, filename)
            
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_files.append(filepath)
            
            # 顯示保存進度
            if len(saved_files) % 10 == 0:
                print(f"已保存 {len(saved_files)} 張圖片...")
        
        return saved_files


def capture_with_animation(video_path: str, output_folder: str, threshold: float = 0.85) -> Tuple[bool, Dict]:
    """快速動畫捕獲接口"""
    capturer = FastAnimationCapture(video_path, output_folder, threshold)
    return capturer.fast_capture()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python fast_animation_capture.py <視頻文件路徑>")
        sys.exit(1)
    
    video_file = sys.argv[1]
    output_dir = f"slides_animation_{os.path.splitext(os.path.basename(video_file))[0]}"
    
    print("使用快速動畫檢測...")
    success, result = capture_with_animation(video_file, output_dir)
    
    if success:
        print(f"\n✅ 完成！")
        print(f"主幻燈片數: {result['main_slides']}")
        print(f"總圖片數: {result['slide_count']}")
        print(f"保存位置: {result['output_folder']}")
    else:
        print(f"\n❌ 失敗: {result.get('error', '未知錯誤')}")