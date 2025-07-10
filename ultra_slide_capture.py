#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
超級幻燈片捕獲模組
專門處理帶動畫效果的幻燈片，能夠捕獲同一張幻燈片的不同動畫狀態
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from skimage.metrics import structural_similarity as ssim
import hashlib
from collections import defaultdict


class UltraSlideCapture:
    """超級幻燈片捕獲類 - 支援動畫檢測"""
    
    def __init__(self, video_path: str, output_folder: str, threshold: float = 0.85):
        self.video_path = video_path
        self.output_folder = output_folder
        self.threshold = threshold
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # 動畫檢測參數
        self.animation_threshold = 0.95  # 動畫檢測的高閾值
        self.region_threshold = 0.02  # 區域變化閾值（2%的像素變化）
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def detect_region_changes(self, img1: np.ndarray, img2: np.ndarray) -> Tuple[bool, float, np.ndarray]:
        """
        檢測兩張圖片之間的區域變化
        返回：(是否有顯著變化, 變化比例, 變化區域mask)
        """
        # 轉換為灰度圖
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # 計算差異
        diff = cv2.absdiff(gray1, gray2)
        
        # 二值化找出變化區域
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # 形態學操作去除噪點
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # 計算變化區域的比例
        change_pixels = np.sum(thresh > 0)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        change_ratio = change_pixels / total_pixels
        
        # 判斷是否為顯著變化（但不是完全不同的幻燈片）
        has_change = self.region_threshold < change_ratio < 0.3  # 2%-30%的變化
        
        return has_change, change_ratio, thresh
    
    def is_animation_sequence(self, frames: List[Tuple[int, np.ndarray]]) -> bool:
        """
        判斷一組幀是否屬於動畫序列
        """
        if len(frames) < 2:
            return False
        
        # 檢查整體相似度是否很高
        similarities = []
        for i in range(len(frames) - 1):
            _, frame1 = frames[i]
            _, frame2 = frames[i + 1]
            
            sim = ssim(
                cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            )
            similarities.append(sim)
        
        # 如果所有相似度都很高（>0.85），可能是動畫序列
        avg_similarity = np.mean(similarities)
        return avg_similarity > 0.85
    
    def detect_content_regions(self, img: np.ndarray) -> Dict[str, np.ndarray]:
        """
        檢測圖片中的內容區域（文字、圖形等）
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 檢測文字區域
        text_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
        text_morph = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, text_kernel)
        _, text_thresh = cv2.threshold(text_morph, 30, 255, cv2.THRESH_BINARY)
        
        # 檢測圖形區域（使用邊緣檢測）
        edges = cv2.Canny(gray, 50, 150)
        
        return {
            'text': text_thresh,
            'edges': edges
        }
    
    def group_animation_frames(self, frames: List[Tuple[int, np.ndarray]]) -> List[List[Tuple[int, np.ndarray]]]:
        """
        將幀分組為幻燈片和其動畫狀態
        """
        if not frames:
            return []
        
        groups = []
        current_group = [frames[0]]
        
        for i in range(1, len(frames)):
            frame_idx, frame = frames[i]
            prev_idx, prev_frame = frames[i-1]
            
            # 計算與前一幀的相似度
            similarity = ssim(
                cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            )
            
            # 檢測區域變化
            has_change, change_ratio, _ = self.detect_region_changes(prev_frame, frame)
            
            # 時間間隔
            time_gap = (frame_idx - prev_idx) / self.fps
            
            # 判斷是否屬於同一組（動畫序列）
            if similarity > self.animation_threshold or (similarity > 0.85 and has_change and time_gap < 10):
                # 高相似度或有局部變化且時間接近，屬於同一組
                current_group.append((frame_idx, frame))
            else:
                # 開始新的組
                groups.append(current_group)
                current_group = [(frame_idx, frame)]
        
        # 添加最後一組
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def ultra_capture(self) -> Tuple[bool, Dict]:
        """使用超級檢測方法捕獲幻燈片（包括動畫狀態）"""
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            
            print(f"開始超級分析視頻：{self.video_path}")
            print(f"總幀數：{self.total_frames}, FPS：{self.fps}")
            print("特色：檢測動畫效果和漸進式內容")
            
            # 第一遍：密集掃描找出所有潛在的變化
            print("\n第一遍：密集掃描變化點...")
            candidate_frames = self.dense_scan()
            
            # 第二遍：智能分組（區分不同幻燈片和動畫狀態）
            print(f"\n第二遍：智能分組 {len(candidate_frames)} 個候選幀...")
            slide_groups = self.group_animation_frames(candidate_frames)
            
            # 第三遍：精選每組中的關鍵幀
            print(f"\n第三遍：從 {len(slide_groups)} 組中精選關鍵幀...")
            final_frames = self.select_key_frames(slide_groups)
            
            # 保存幻燈片
            print(f"\n保存幻燈片和動畫狀態...")
            saved_files = self.save_slides_with_animation(final_frames)
            
            return True, {
                "output_folder": self.output_folder,
                "slide_count": len(saved_files),
                "saved_files": saved_files,
                "total_frames": self.total_frames,
                "slide_groups": len(slide_groups),
                "detection_time": time.time()
            }
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def dense_scan(self, step: int = 15) -> List[Tuple[int, np.ndarray]]:
        """密集掃描，使用較小步長找出所有變化"""
        candidate_frames = []
        prev_frame = None
        last_saved_idx = -1
        
        # 動態調整步長
        if self.total_frames > 10000:
            step = 30
        elif self.total_frames < 1000:
            step = 10
        
        print(f"使用步長：{step} 幀 ({step/self.fps:.1f}秒)")
        
        for i in range(0, self.total_frames, step):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            # 縮小圖片以加快處理
            small_frame = cv2.resize(frame, (640, 480))
            
            if prev_frame is not None:
                # 計算整體相似度
                similarity = ssim(
                    cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                )
                
                # 檢測區域變化
                has_change, change_ratio, _ = self.detect_region_changes(prev_frame, small_frame)
                
                # 判斷是否需要保存
                should_save = False
                
                if similarity < self.threshold:
                    # 明顯不同的幻燈片
                    should_save = True
                elif has_change and (i - last_saved_idx) > self.fps * 2:
                    # 有區域變化且距離上次保存超過2秒
                    should_save = True
                
                if should_save:
                    # 精確定位變化點
                    for offset in range(-step//2, step//2 + 1, 3):
                        check_idx = i + offset
                        if 0 <= check_idx < self.total_frames:
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, check_idx)
                            ret, check_frame = self.cap.read()
                            if ret:
                                candidate_frames.append((check_idx, check_frame.copy()))
                    last_saved_idx = i
            else:
                # 第一幀
                candidate_frames.append((i, frame.copy()))
                last_saved_idx = i
            
            prev_frame = small_frame
            
            # 顯示進度
            if i % (step * 20) == 0:
                progress = (i / self.total_frames) * 100
                print(f"掃描進度：{progress:.1f}%")
        
        # 去重
        unique_frames = []
        frame_hashes = set()
        
        for idx, frame in candidate_frames:
            # 計算幀的哈希值
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (16, 16))
            frame_hash = hashlib.md5(resized.tobytes()).hexdigest()
            
            if frame_hash not in frame_hashes:
                frame_hashes.add(frame_hash)
                unique_frames.append((idx, frame))
        
        print(f"找到 {len(unique_frames)} 個獨特的候選幀")
        return sorted(unique_frames, key=lambda x: x[0])
    
    def select_key_frames(self, slide_groups: List[List[Tuple[int, np.ndarray]]]) -> List[List[Tuple[int, np.ndarray]]]:
        """從每個組中選擇關鍵幀"""
        final_groups = []
        
        for group_idx, group in enumerate(slide_groups):
            if len(group) == 1:
                # 只有一幀，直接保留
                final_groups.append(group)
            else:
                # 多幀組，選擇關鍵幀
                key_frames = []
                
                # 保留第一幀
                key_frames.append(group[0])
                
                # 檢測組內的顯著變化
                prev_content = self.detect_content_regions(group[0][1])
                
                for i in range(1, len(group)):
                    frame_idx, frame = group[i]
                    curr_content = self.detect_content_regions(frame)
                    
                    # 比較內容區域的變化
                    text_diff = cv2.absdiff(prev_content['text'], curr_content['text'])
                    edge_diff = cv2.absdiff(prev_content['edges'], curr_content['edges'])
                    
                    text_change = np.sum(text_diff > 0) / text_diff.size
                    edge_change = np.sum(edge_diff > 0) / edge_diff.size
                    
                    # 如果有顯著的內容變化，保留這一幀
                    if text_change > 0.01 or edge_change > 0.01:
                        key_frames.append((frame_idx, frame))
                        prev_content = curr_content
                
                # 如果組內有多個關鍵幀，保留
                if len(key_frames) > 1:
                    final_groups.append(key_frames)
                else:
                    # 否則只保留第一幀和最後一幀
                    if len(group) > 1:
                        key_frames.append(group[-1])
                    final_groups.append(key_frames)
        
        return final_groups
    
    def save_slides_with_animation(self, slide_groups: List[List[Tuple[int, np.ndarray]]]) -> List[str]:
        """保存幻燈片，包括動畫狀態"""
        saved_files = []
        
        for group_idx, group in enumerate(slide_groups):
            slide_num = group_idx + 1
            
            if len(group) == 1:
                # 單一幀
                frame_idx, frame = group[0]
                timestamp = frame_idx / self.fps
                filename = f"slide_{slide_num:03d}_t{timestamp:.1f}s.jpg"
                filepath = os.path.join(self.output_folder, filename)
                
                cv2.imwrite(filepath, frame)
                saved_files.append(filepath)
                
                print(f"保存幻燈片 {slide_num}: {filename}")
            else:
                # 動畫序列
                print(f"幻燈片 {slide_num} 包含 {len(group)} 個動畫狀態")
                
                for sub_idx, (frame_idx, frame) in enumerate(group):
                    timestamp = frame_idx / self.fps
                    # 使用 slide_X_Y 格式命名動畫序列
                    filename = f"slide_{slide_num:03d}_{sub_idx+1}_t{timestamp:.1f}s.jpg"
                    filepath = os.path.join(self.output_folder, filename)
                    
                    cv2.imwrite(filepath, frame)
                    saved_files.append(filepath)
                    
                    print(f"  保存動畫狀態 {sub_idx+1}: {filename}")
        
        return saved_files


def capture_slides_ultra(video_path: str, output_folder: str, threshold: float = 0.85) -> Tuple[bool, Dict]:
    """超級幻燈片捕獲函數接口"""
    capturer = UltraSlideCapture(video_path, output_folder, threshold)
    return capturer.ultra_capture()


if __name__ == "__main__":
    # 測試代碼
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python ultra_slide_capture.py <視頻文件路徑>")
        sys.exit(1)
    
    video_file = sys.argv[1]
    output_dir = f"slides_ultra_{os.path.splitext(os.path.basename(video_file))[0]}"
    
    print("使用超級捕獲方法（檢測動畫效果）...")
    success, result = capture_slides_ultra(video_file, output_dir)
    
    if success:
        print(f"\n成功捕獲 {result['slide_count']} 張幻燈片（含動畫狀態）")
        print(f"幻燈片組數: {result['slide_groups']}")
        print(f"保存位置: {result['output_folder']}")
    else:
        print(f"\n捕獲失敗: {result.get('error', '未知錯誤')}")