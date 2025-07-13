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
import json
from collections import defaultdict


class ImprovedSlideCapture:
    """改進的幻燈片捕獲類"""
    
    def __init__(self, video_path: str, output_folder: str, threshold: float = 0.85):
        self.video_path = video_path
        self.output_folder = output_folder
        self.threshold = threshold
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.similarity_groups = defaultdict(list)  # 存儲相似圖片分組
        self.metadata = []  # 存儲幻燈片元數據
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def calculate_phash(self, img: np.ndarray, hash_size: int = 8) -> str:
        """計算感知哈希（pHash）"""
        # 轉換為灰度圖
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # 調整大小到 hash_size x hash_size
        resized = cv2.resize(gray, (hash_size, hash_size))
        
        # 計算DCT
        dct_result = cv2.dct(np.float32(resized))
        
        # 只保留左上角的低頻部分
        dct_low = dct_result[:hash_size, :hash_size]
        
        # 計算平均值（排除第一個元素）
        avg = np.mean(dct_low[1:, 1:])
        
        # 生成哈希
        hash_bits = (dct_low > avg).flatten()
        
        # 轉換為十六進制字符串
        hash_int = 0
        for bit in hash_bits:
            hash_int = (hash_int << 1) | int(bit)
        
        return format(hash_int, f'0{hash_size*hash_size//4}x')
    
    def calculate_phash_similarity(self, hash1: str, hash2: str) -> float:
        """計算兩個感知哈希的相似度"""
        # 將十六進制轉換為二進制
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
        
        # 計算漢明距離
        xor = int1 ^ int2
        hamming_distance = bin(xor).count('1')
        
        # 轉換為相似度（0-1之間）
        max_distance = len(hash1) * 4  # 每個十六進制字符有4位
        similarity = 1 - (hamming_distance / max_distance)
        
        return similarity
    
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
        
        # 最終去重和分組（使用感知哈希）
        unique_frames = []
        frame_data = []  # 存儲幀數據和哈希
        
        # 計算所有幀的感知哈希
        for frame_idx, frame in final_frames:
            phash = self.calculate_phash(frame)
            frame_data.append({
                'frame_idx': frame_idx,
                'frame': frame,
                'phash': phash,
                'group': -1  # 初始未分組
            })
        
        # 進行相似性分組
        group_id = 0
        for i, data in enumerate(frame_data):
            if data['group'] == -1:  # 未分組
                data['group'] = group_id
                # 檢查後續幀是否相似
                for j in range(i + 1, len(frame_data)):
                    if frame_data[j]['group'] == -1:
                        similarity = self.calculate_phash_similarity(
                            data['phash'], 
                            frame_data[j]['phash']
                        )
                        if similarity > 0.9:  # 90%相似度閾值
                            frame_data[j]['group'] = group_id
                group_id += 1
        
        # 每組只保留最清晰的一張（基於拉普拉斯變換）
        groups = defaultdict(list)
        for data in frame_data:
            groups[data['group']].append(data)
        
        for group_id, group_frames in groups.items():
            if len(group_frames) == 1:
                unique_frames.append((group_frames[0]['frame_idx'], group_frames[0]['frame']))
            else:
                # 選擇最清晰的幀
                best_frame = max(group_frames, key=lambda x: cv2.Laplacian(
                    cv2.cvtColor(x['frame'], cv2.COLOR_BGR2GRAY), cv2.CV_64F
                ).var())
                unique_frames.append((best_frame['frame_idx'], best_frame['frame']))
                # 記錄相似幀信息
                self.similarity_groups[group_id] = [
                    (f['frame_idx'], f['phash']) for f in group_frames
                ]
        
        # 按時間排序
        unique_frames.sort(key=lambda x: x[0])
        
        return unique_frames
    
    def save_slides(self, slide_frames: List[Tuple[int, np.ndarray]]) -> List[str]:
        """保存幻燈片並生成元數據"""
        saved_files = []
        
        # 確保按時間排序
        slide_frames.sort(key=lambda x: x[0])
        
        # 查找每個幀所屬的組
        frame_to_group = {}
        for group_id, frames in self.similarity_groups.items():
            for frame_idx, _ in frames:
                frame_to_group[frame_idx] = group_id
        
        for idx, (frame_idx, frame) in enumerate(slide_frames):
            timestamp = frame_idx / self.fps
            phash = self.calculate_phash(frame)
            
            # 轉換時間格式
            minutes = int(timestamp / 60)
            seconds = timestamp % 60
            
            # 生成文件名 - 統一格式，按時間順序
            group_id = frame_to_group.get(frame_idx, -1)
            if group_id != -1:
                # 有相似組的情況
                filename = f"slide_{idx+1:03d}_t{minutes}m{seconds:.1f}s_g{group_id:02d}_h{phash[:8]}.jpg"
            else:
                # 獨立幻燈片
                filename = f"slide_{idx+1:03d}_t{minutes}m{seconds:.1f}s_h{phash[:8]}.jpg"
            
            filepath = os.path.join(self.output_folder, filename)
            
            # 保存圖片
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_files.append(filepath)
            
            # 收集元數據
            self.metadata.append({
                'index': idx + 1,
                'filename': filename,
                'frame_index': frame_idx,
                'timestamp': timestamp,
                'phash': phash,
                'group_id': group_id,
                'similar_frames': self.similarity_groups.get(group_id, [])
            })
            
            print(f"保存幻燈片 {idx+1}/{len(slide_frames)}: {filename} (時間: {minutes}:{seconds:05.1f})")
        
        # 保存元數據文件
        metadata_path = os.path.join(self.output_folder, 'slides_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                'video_path': self.video_path,
                'total_frames': self.total_frames,
                'fps': self.fps,
                'threshold': self.threshold,
                'slides': self.metadata,
                'similarity_groups': {
                    str(k): v for k, v in self.similarity_groups.items()
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n元數據已保存到: {metadata_path}")
        
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