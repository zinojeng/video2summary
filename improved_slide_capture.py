#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
改進的幻燈片捕獲模組
使用多種檢測策略和優化方法來提高速度和準確性
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from skimage.metrics import structural_similarity as ssim
import hashlib


class ImprovedSlideCapture:
    """改進的幻燈片捕獲類"""
    
    def __init__(self, video_path: str, output_folder: str, threshold: float = 0.85):
        self.video_path = video_path
        self.output_folder = output_folder
        self.threshold = threshold
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def calculate_histogram_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """計算兩張圖片的直方圖差異（快速）"""
        # 轉換為灰度圖
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # 計算直方圖
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        # 歸一化
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        # 計算相關性（1.0 表示完全相同）
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    
    def calculate_edge_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """計算邊緣檢測的差異（檢測結構變化）"""
        # 轉換為灰度圖
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # 邊緣檢測
        edges1 = cv2.Canny(gray1, 50, 150)
        edges2 = cv2.Canny(gray2, 50, 150)
        
        # 計算差異
        diff = cv2.absdiff(edges1, edges2)
        return 1.0 - (np.sum(diff) / (diff.shape[0] * diff.shape[1] * 255))
    
    def detect_text_regions(self, img: np.ndarray) -> int:
        """檢測圖片中的文字區域數量（用於檢測內容豐富的幻燈片）"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 使用形態學操作來檢測文字區域
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
        morph = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
        
        # 二值化
        _, thresh = cv2.threshold(morph, 30, 255, cv2.THRESH_BINARY)
        
        # 尋找輪廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 過濾有效的文字區域
        text_regions = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # 過濾太小的區域
                text_regions += 1
        
        return text_regions
    
    def multi_strategy_capture(self) -> Tuple[bool, Dict]:
        """使用多種策略的快速捕獲方法"""
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            
            print(f"開始分析視頻：{self.video_path}")
            print(f"總幀數：{self.total_frames}, FPS：{self.fps}")
            
            # 第一遍：快速掃描，找出可能的變化點
            print("\n第一遍：快速掃描...")
            candidate_frames = self.fast_scan()
            
            # 第二遍：精確檢測候選幀
            print(f"\n第二遍：精確檢測 {len(candidate_frames)} 個候選點...")
            slide_frames = self.precise_detection(candidate_frames)
            
            # 第三遍：補充檢測（確保不遺漏）
            print("\n第三遍：補充檢測...")
            final_frames = self.supplementary_detection(slide_frames)
            
            # 保存幻燈片
            print(f"\n保存 {len(final_frames)} 張幻燈片...")
            saved_files = self.save_slides(final_frames)
            
            return True, {
                "output_folder": self.output_folder,
                "slide_count": len(saved_files),
                "saved_files": saved_files,
                "total_frames": self.total_frames,
                "detection_time": time.time()
            }
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def fast_scan(self, step: int = 30) -> List[int]:
        """快速掃描，使用大步長找出可能的變化點"""
        candidate_frames = []
        prev_frame = None
        
        # 動態調整步長（視頻越長，步長越大）
        if self.total_frames > 10000:
            step = 60
        elif self.total_frames > 5000:
            step = 45
        
        for i in range(0, self.total_frames, step):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            # 縮小圖片以加快處理速度
            small_frame = cv2.resize(frame, (320, 240))
            
            if prev_frame is not None:
                # 使用直方圖快速比較
                hist_similarity = self.calculate_histogram_diff(prev_frame, small_frame)
                
                # 如果差異較大，標記為候選
                if hist_similarity < 0.95:
                    # 添加變化點前後的幀作為候選
                    for offset in range(-step//2, step//2 + 1, 5):
                        candidate_frame = i + offset
                        if 0 <= candidate_frame < self.total_frames:
                            candidate_frames.append(candidate_frame)
            
            prev_frame = small_frame
            
            # 顯示進度
            if i % (step * 10) == 0:
                progress = (i / self.total_frames) * 100
                print(f"快速掃描進度：{progress:.1f}%")
        
        # 去重並排序
        candidate_frames = sorted(list(set(candidate_frames)))
        return candidate_frames
    
    def precise_detection(self, candidate_frames: List[int]) -> List[Tuple[int, np.ndarray]]:
        """對候選幀進行精確檢測"""
        slide_frames = []
        prev_frame = None
        prev_frame_idx = -1
        
        for idx, frame_idx in enumerate(candidate_frames):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            is_new_slide = False
            
            if prev_frame is None:
                is_new_slide = True
            else:
                # 使用多種方法綜合判斷
                ssim_score = ssim(
                    cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                )
                edge_similarity = self.calculate_edge_diff(prev_frame, frame)
                
                # 檢測文字區域變化
                text_regions_prev = self.detect_text_regions(prev_frame)
                text_regions_curr = self.detect_text_regions(frame)
                text_change = abs(text_regions_curr - text_regions_prev) > 5
                
                # 綜合判斷
                if (ssim_score < self.threshold or 
                    edge_similarity < 0.9 or 
                    text_change):
                    is_new_slide = True
            
            if is_new_slide and (frame_idx - prev_frame_idx) > self.fps:  # 至少間隔1秒
                slide_frames.append((frame_idx, frame.copy()))
                prev_frame = frame
                prev_frame_idx = frame_idx
            
            # 顯示進度
            if idx % 50 == 0:
                progress = (idx / len(candidate_frames)) * 100
                print(f"精確檢測進度：{progress:.1f}%")
        
        return slide_frames
    
    def supplementary_detection(self, slide_frames: List[Tuple[int, np.ndarray]]) -> List[Tuple[int, np.ndarray]]:
        """補充檢測，確保不遺漏重要幻燈片"""
        final_frames = slide_frames.copy()
        
        # 檢查相鄰幻燈片之間的間隔
        for i in range(len(slide_frames) - 1):
            frame_idx1, _ = slide_frames[i]
            frame_idx2, _ = slide_frames[i + 1]
            
            gap = frame_idx2 - frame_idx1
            
            # 如果間隔太大（超過30秒），進行補充檢測
            if gap > self.fps * 30:
                print(f"檢測到大間隔：{gap/self.fps:.1f}秒，進行補充檢測...")
                
                # 在間隔中進行更細緻的檢測
                for check_idx in range(frame_idx1 + int(self.fps * 5), 
                                     frame_idx2, 
                                     int(self.fps * 5)):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, check_idx)
                    ret, frame = self.cap.read()
                    
                    if ret:
                        # 與前後幻燈片比較
                        is_different = True
                        for _, existing_frame in slide_frames[max(0, i-2):min(len(slide_frames), i+3)]:
                            similarity = ssim(
                                cv2.cvtColor(existing_frame, cv2.COLOR_BGR2GRAY),
                                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            )
                            if similarity > 0.95:
                                is_different = False
                                break
                        
                        if is_different:
                            final_frames.append((check_idx, frame.copy()))
        
        # 重新排序
        final_frames.sort(key=lambda x: x[0])
        
        # 最終去重（使用圖片哈希）
        unique_frames = []
        frame_hashes = set()
        
        for frame_idx, frame in final_frames:
            # 計算圖片哈希
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (8, 8))
            frame_hash = hashlib.md5(resized.tobytes()).hexdigest()
            
            if frame_hash not in frame_hashes:
                frame_hashes.add(frame_hash)
                unique_frames.append((frame_idx, frame))
        
        return unique_frames
    
    def save_slides(self, slide_frames: List[Tuple[int, np.ndarray]]) -> List[str]:
        """保存幻燈片"""
        saved_files = []
        
        for idx, (frame_idx, frame) in enumerate(slide_frames):
            timestamp = frame_idx / self.fps
            filename = f"slide_{idx+1:03d}_t{timestamp:.1f}s.jpg"
            filepath = os.path.join(self.output_folder, filename)
            
            cv2.imwrite(filepath, frame)
            saved_files.append(filepath)
            
            print(f"保存幻燈片 {idx+1}/{len(slide_frames)}: {filename}")
        
        return saved_files


def capture_slides_improved(video_path: str, output_folder: str, threshold: float = 0.85) -> Tuple[bool, Dict]:
    """改進的幻燈片捕獲函數接口"""
    capturer = ImprovedSlideCapture(video_path, output_folder, threshold)
    return capturer.multi_strategy_capture()


if __name__ == "__main__":
    # 測試代碼
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python improved_slide_capture.py <視頻文件路徑>")
        sys.exit(1)
    
    video_file = sys.argv[1]
    output_dir = f"slides_{os.path.splitext(os.path.basename(video_file))[0]}"
    
    print("使用改進的方法捕獲幻燈片...")
    success, result = capture_slides_improved(video_file, output_dir)
    
    if success:
        print(f"\n成功捕獲 {result['slide_count']} 張幻燈片")
        print(f"保存位置: {result['output_folder']}")
    else:
        print(f"\n捕獲失敗: {result.get('error', '未知錯誤')}")