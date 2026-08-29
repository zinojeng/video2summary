#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
改進的幻燈片捕獲模組
使用多種檢測策略和優化方法來提高速度和準確性
包含：並行處理、模糊檢測、去重優化
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from skimage.metrics import structural_similarity as ssim
import hashlib
import json
from collections import defaultdict


def calculate_phash(img: np.ndarray, hash_size: int = 8) -> str:
    """靜態方法：計算感知哈希（pHash）"""
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


def is_blurry(img: np.ndarray, threshold: float = 100.0) -> Tuple[bool, float]:
    """靜態方法：檢測圖片是否模糊 (使用 Laplacian Variance)"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance < threshold, variance


def detect_and_crop_slide(frame: np.ndarray) -> Tuple[np.ndarray, bool, str]:
    """
    檢測並裁剪幻燈片區域 (增強版)
    移除嚴格的四邊形檢測，改用邊界框 + 實心度 + 長寬比判斷
    """
    try:
        if frame is None:
            return frame, False, "Empty frame"
            
        height, width = frame.shape[:2]
        frame_area = width * height
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # 稍微加強對比度可能有助於邊緣檢測
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
        except:
            pass # fallback
            
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 使用 Canny 檢測邊緣，參數稍微放寬
        edges = cv2.Canny(blurred, 30, 150)
        
        # 膨脹邊緣以連接斷裂的線條
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # 尋找輪廓
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 按面積排序 (從大到小)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 過濾太小的區域 (例如小於畫面的 10%)
            if area < (frame_area * 0.1):
                continue
                
            x, y, w, h = cv2.boundingRect(contour)
            rect_area = w * h
            
            # 1. 檢查長寬比 (Aspect Ratio)
            # 16:9 = 1.77, 4:3 = 1.33
            # 我們設定寬鬆範圍 1.2 ~ 2.4以涵蓋大部分投影片
            aspect_ratio = float(w) / h
            if not (1.2 < aspect_ratio < 2.4):
                continue
            
            # 2. 檢查實心度 (Solidity) - 輪廓面積與邊界框面積的比值
            # 矩形的實心度應該接近 1
            solidity = float(area) / rect_area
            if solidity < 0.85: # 如果形狀很不規則，可能不是 Slide
                continue
                
            # 3. 檢查是否佔滿全螢幕 (如果是全螢幕通常不需要裁，或者就是原圖)
            # 但如果使用者堅持要「識別」，我們需要區分「全螢幕Slide」和「包含Slide的畫面」
            # 如果邊界框幾乎等於原圖 (>98%)，我們視為未裁剪
            if rect_area > (frame_area * 0.98):
                continue
                
            # 去除紅色/雜色邊框：內縮幾個像素
            margin = 8
            x = max(0, x + margin)
            y = max(0, y + margin)
            w = max(1, w - 2 * margin)
            h = max(1, h - 2 * margin)
                
            # 找到了符合條件的區域
            cropped = frame[y:y+h, x:x+w]
            info = f"Cropped: {w}x{h} (AR: {aspect_ratio:.2f}, Sol: {solidity:.2f})"
            return cropped, True, info
                    
        return frame, False, "No slide detected"
        
    except Exception as e:
        print(f"Crop error: {e}")
        return frame, False, f"Error: {e}"



def has_slide_content(frame) -> Tuple[bool, str]:
    """
    啟發式檢查：判斷畫面是否包含幻燈片特徵 (文字行、邊框、圖表)
    過濾掉只有人物/演講者的畫面 (自然場景通常缺乏長直線)
    """
    try:
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. 邊緣檢測
        edges = cv2.Canny(gray, 50, 150)
        
        # 2. 檢測直線 (Hough Transform)
        # minLineLength: 線段最短長度 (像素)，文字行或邊框通常較長 (> width/20)
        # maxLineGap: 線段允許斷裂的距離
        min_line_len = min(width, height) * 0.05
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                              minLineLength=min_line_len, maxLineGap=10)
        
        if lines is None:
            return False, "No structural lines detected"
        
        # 3. 統計水平與垂直線的數量
        # 幻燈片通常充滿文字(水平線)和排版框(垂直線)
        # 自然人物場景則是雜亂角度的短線
        hv_lines = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            # 水平 (0度/180度) 或 垂直 (90度) (容許誤差 +/- 10度)
            if angle < 10 or angle > 170 or (80 < angle < 100):
                hv_lines += 1
        
        # 閾值設定：至少要有 4 條明顯的結構線 (例如一個邊框就有4條，或是幾行字)
        if hv_lines >= 4:
            return True, f"Found {hv_lines} H/V lines"
        else:
            return False, f"Not enough H/V lines ({hv_lines} < 4)"
            
    except Exception as e:
        # 出錯時保守起見，保留畫面
        return True, f"Check error: {str(e)}"


def worker_scan_segment(video_path: str, start_frame: int, end_frame: int, step: int, threshold: float, quick_check: bool = False) -> List[Dict]:
    """工作進程：掃描指定片段並返回候選幀信息"""
    results = []
    cap = cv2.VideoCapture(video_path)
    
    try:
        # === 優化：Gap Integrity Check (快速檢查) ===
        # 如果開啟 quick_check，先比對頭尾。如果頭尾極度相似，假設中間無變化，直接跳過。
        # 這能大幅加速靜態長 Slide 的處理。
        if quick_check and (end_frame - start_frame) > step:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            ret1, frame_start = cap.read()
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, end_frame - 1)
            ret2, frame_end = cap.read()
            
            if ret1 and ret2:
                # 使用小圖比對
                s_start = cv2.resize(frame_start, (64, 36))
                s_end = cv2.resize(frame_end, (64, 36))
                
                g1 = cv2.cvtColor(s_start, cv2.COLOR_BGR2GRAY)
                g2 = cv2.cvtColor(s_end, cv2.COLOR_BGR2GRAY)
                
                h1 = cv2.calcHist([g1], [0], None, [256], [0, 256])
                h2 = cv2.calcHist([g2], [0], None, [256], [0, 256])
                cv2.normalize(h1, h1)
                cv2.normalize(h2, h2)
                sim = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
                
                # 如果頭尾相似度極高 (>0.995)，視為靜態區間，直接跳過
                if sim > 0.995:
                    return []
        
        total_segment_frames = end_frame - start_frame
        
        # 1. 快速掃描 (Fast Scan)
        candidates = []
        prev_hist_frame = None
        
        # 確保從 start_frame 開始
        current_pos = start_frame
        
        last_print_time = time.time()
        
        while current_pos < end_frame:
            # 顯示進度 (每隔一段時間或一定幀數)
            if (current_pos - start_frame) % (step * 20) == 0:
                # 只在非 quick_check 模式或長任務才顯示，避免 log 混亂
                if not quick_check and time.time() - last_print_time > 3.0:
                    progress = (current_pos - start_frame) / total_segment_frames * 100
                    print(f"  ... 正在掃描 {start_frame}-{end_frame} 區間: {progress:.1f}%", flush=True)
                    last_print_time = time.time()

            cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
            ret, frame = cap.read()
            if not ret:
                break
            
            # 縮小圖片以加快處理速度
            small_frame = cv2.resize(frame, (128, 72))
            
            if prev_hist_frame is not None:
                # 計算直方圖差異
                gray1 = cv2.cvtColor(prev_hist_frame, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
                hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
                cv2.normalize(hist1, hist1)
                cv2.normalize(hist2, hist2)
                hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
                
                # 動態閾值調整
                # 如果步長很小 (Ultra模式)，我們對差異更敏感 (即便微小差異也算候選)
                hist_thresh = 0.995 if step <= 5 else 0.985
                
                # 如果差異較大，標記為候選區域
                if hist_similarity < hist_thresh:
                    # 添加變化點前後的幀
                    for offset in range(-step//2, step//2 + 1, max(1, step//5)):
                        candidate_idx = current_pos + offset
                        if start_frame <= candidate_idx < end_frame:
                            candidates.append(candidate_idx)
            else:
                # 每個片段的第一幀總是候選
                candidates.append(current_pos)
                
            prev_hist_frame = small_frame
            current_pos += step
            
        # 去重並排序
        candidates = sorted(list(set(candidates)))
        
        # 2. 精確檢測 (Precise Detection)
        if not candidates:
            return []
            
        prev_valid_frame = None
        
        for frame_idx in candidates:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            # 內容過濾：是否像 Slide？
            # 這能有效過濾掉只有演講者在討論的畫面 (缺乏結構線)
            is_slide, reason = has_slide_content(frame)
            if not is_slide:
                # print(f"Skipped frame {frame_idx} (segment {start_frame}-{end_frame}): {reason}") # Debug print
                continue

            # 模糊檢測
            blurry, var = is_blurry(frame)
            if blurry and var < 50.0: # 只過濾非常模糊的
                continue
                
            is_new_slide = False
            phash = calculate_phash(frame)
            
            if prev_valid_frame is None:
                is_new_slide = True
            else:
                # SSIM 比較
                gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_prev = cv2.cvtColor(prev_valid_frame, cv2.COLOR_BGR2GRAY)
                
                score = ssim(gray_prev, gray_curr)
                
                # 邊緣差異
                edges1 = cv2.Canny(gray_prev, 50, 150)
                edges2 = cv2.Canny(gray_curr, 50, 150)
                diff = cv2.absdiff(edges1, edges2)
                edge_similarity = 1.0 - (np.sum(diff) / (diff.size * 255))
                
                if score < threshold or edge_similarity < 0.95: # edge sim 也提高標準
                    is_new_slide = True
            
            if is_new_slide:
                # 存儲候選結果 (不存完整大圖，只存必要信息以減少 IPC 開銷)
                results.append({
                    'frame_idx': frame_idx,
                    'phash': phash,
                    'is_blurry': blurry,
                    'blur_var': var
                })
                prev_valid_frame = frame

    except Exception as e:
        print(f"Worker process error at {start_frame}-{end_frame}: {e}")
    finally:
        cap.release()
        
    return results


class ImprovedSlideCapture:
    """改進的幻燈片捕獲類 (並行版)"""
    
    def __init__(self, video_path: str, output_folder: str, threshold: float = 0.85, ultra_mode: bool = False, smart_mode: bool = False):
        self.video_path = video_path
        self.output_folder = output_folder
        self.threshold = threshold
        self.ultra_mode = ultra_mode
        self.smart_mode = smart_mode
        self.similarity_groups = defaultdict(list)
        self.metadata = []
        
        # 獲取視頻信息
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"無法打開視頻: {video_path}")
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
    def calculate_phash_similarity(self, hash1: str, hash2: str) -> float:
        """計算兩個感知哈希的相似度"""
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
        xor = int1 ^ int2
        hamming_distance = bin(xor).count('1')
        max_distance = len(hash1) * 4
        return 1 - (hamming_distance / max_distance)
    
    def multi_strategy_capture(self) -> Tuple[bool, Dict]:
        """使用並行處理的快速捕獲方法"""
        try:
            start_time = time.time()
            os.makedirs(self.output_folder, exist_ok=True)
            
            print(f"開始分析視頻：{self.video_path}")
            print(f"總幀數：{self.total_frames}, FPS：{self.fps:.2f}")
            
            # 設定 CPU 核心數
            cpu_count = min(os.cpu_count() or 4, 8)
            print(f"使用 {cpu_count} 個進程進行並行處理...")
            
            all_candidates = []

            # === 策略選擇 ===
            if self.ultra_mode:
                print("⚡️ Ultra Mode 啟動: 執行單次高密度全域掃描...")
                step = 4
                thresh = 0.99
                segments = self._create_segments(self.total_frames, cpu_count)
                all_candidates = self._run_parallel_scan(segments, step, thresh, cpu_count)
                
            elif self.smart_mode:
                print("🧠 Smart Mode 啟動: 執行雙重混合掃描 (速度+完整性)...")
                
                # Pass 1: 快速掃描 (Coarse Scan)
                print("--- 階段 1: 快速全域掃描 ---")
                step1 = 45 # 較大的步長 (約1.5秒)
                thresh1 = 0.90
                segments1 = self._create_segments(self.total_frames, cpu_count)
                candidates1 = self._run_parallel_scan(segments1, step1, thresh1, cpu_count)
                print(f"   初步發現 {len(candidates1)} 個潛在變化點")
                
                # Pass 2: 間隙填補 (Gap Filling)
                print("--- 階段 2: 智能間隙填補 ---")
                candidates1.sort(key=lambda x: x['frame_idx'])
                
                # 提取幀號用於計算間隙
                candidate_indices = [c['frame_idx'] for c in candidates1]
                
                gaps = []
                gap_threshold = int(self.fps * 15) # 超過 15 秒的間隙
                
                # 檢查所有已知候選點之間的間隙
                check_points = [0] + candidate_indices + [self.total_frames]
                for i in range(len(check_points) - 1):
                    start = check_points[i]
                    end = check_points[i+1]
                    if (end - start) > gap_threshold:
                        # 為了避免重複邊界，稍微內縮
                        gaps.append((self.video_path, start + step1, end - step1))
                if gaps:
                    print(f"   發現 {len(gaps)} 個長間隙，進行高密度掃描...")
                    # 重新分配 gaps 給 workers (這些不是均勻片段，而是特定區域)
                    # 我們直接將 gaps 作為任務清單
                    step2 = 10 # 優化：不需要每 6 幀，10 幀 (0.3s) 足夠
                    thresh2 = 0.99
                    
                    # Gap Integrity Check: 傳入 True 開啟頭尾快速檢查
                    gap_tasks = [(self.video_path, g[1], g[2], step2, thresh2, True) for g in gaps]
                    
                    with multiprocessing.Pool(processes=cpu_count) as pool:
                        gap_results = pool.starmap(worker_scan_segment, gap_tasks)
                        for res in gap_results:
                            candidates1.extend(res)
                
                all_candidates = candidates1
                
            else:
                # 一般模式
                print("執行標準掃描...")
                step = 15
                if self.total_frames > 20000: step = 30
                if self.total_frames > 100000: step = 60
                
                segments = self._create_segments(self.total_frames, cpu_count)
                all_candidates = self._run_parallel_scan(segments, step, self.threshold, cpu_count)
            
            print(f"\n掃描完成，初步找到 {len(all_candidates)} 個候選幀")
            print("進行全局去重與合併...")
            
            final_frames = self.merge_and_deduplicate(all_candidates)
            
            print(f"\n保存 {len(final_frames)} 張幻燈片...")
            saved_files = self.save_slides(final_frames)
            
            elapsed = time.time() - start_time
            return True, {
                "output_folder": self.output_folder,
                "slide_count": len(saved_files),
                "saved_files": saved_files,
                "total_frames": self.total_frames,
                "detection_time": elapsed,
                "fps": self.fps
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, {"error": str(e)}

    def _create_segments(self, total_frames, count) -> List[Tuple]:
        segment_length = total_frames // count
        segments = []
        overlap = int(self.fps * 5)
        for i in range(count):
            start = i * segment_length
            end = (i + 1) * segment_length if i < count - 1 else total_frames
            actual_end = min(end + overlap, total_frames)
            segments.append((self.video_path, start, actual_end))
        return segments

    def _run_parallel_scan(self, segments, step, threshold, cpu_count) -> List[Dict]:
        all_res = []
        with multiprocessing.Pool(processes=cpu_count) as pool:
            # 傳入 False 表示不啟用 Gap Integrity Check (標準掃描不應跳過)
            tasks = [(s[0], s[1], s[2], step, threshold, False) for s in segments]
            results = pool.starmap(worker_scan_segment, tasks)
            for res in results:
                all_res.extend(res)
        return all_res
            
    def merge_and_deduplicate(self, candidates: List[Dict]) -> List[int]:
        """合併並行結果並進行全局去重"""
        if not candidates:
            return []
            
        # 按幀號排序
        candidates.sort(key=lambda x: x['frame_idx'])
        
        unique_indices = []
        prev_phash = None
        last_frame_idx = -1
        min_interval = int(self.fps * 1.5)  # 最小間隔 1.5 秒
        
        for cand in candidates:
            frame_idx = cand['frame_idx']
            phash = cand['phash']
            
            # 1. 時間間隔檢查 (對於非常接近的幀，只保留最清晰的或第一個)
            if last_frame_idx != -1 and (frame_idx - last_frame_idx) < min_interval:
                continue
                
            # 2. 全局哈希去重
            is_duplicate = False
            if prev_phash is not None:
                sim = self.calculate_phash_similarity(prev_phash, phash)
                if sim > 0.96:  # 提高去重閾值，避免誤刪相似但不同的Slide (e.g. 0.92 -> 0.96)
                    is_duplicate = True
            
            if not is_duplicate:
                unique_indices.append(frame_idx)
                prev_phash = phash
                last_frame_idx = frame_idx
                
        return unique_indices

    def save_slides(self, frame_indices: List[int]) -> List[str]:
        """從視頻中提取並保存最終幻燈片"""
        saved_files = []
        cap = cv2.VideoCapture(self.video_path)
        
        try:
            # 重新計算哈希用於分組
            frame_data = []
            
            print("提取高清原圖...")
            for i, idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    phash = calculate_phash(frame)
                    frame_data.append({
                        'frame_idx': idx,
                        'frame': frame,
                        'phash': phash,
                        'group': -1
                    })
                    if i % 10 == 0:
                        print(f"提取進度: {i}/{len(frame_indices)}")
            
            # 進行相似性分組
            group_id = 0
            for i, data in enumerate(frame_data):
                if data['group'] == -1:
                    data['group'] = group_id
                    for j in range(i + 1, len(frame_data)):
                        if frame_data[j]['group'] == -1:
                            sim = self.calculate_phash_similarity(data['phash'], frame_data[j]['phash'])
                            if sim > 0.9:
                                frame_data[j]['group'] = group_id
                    group_id += 1
            
            # 保存
            for data in frame_data:
                idx = data['frame_idx']
                original_frame = data['frame']
                phash = data['phash']
                gid = data['group']
                
                # 自動裁剪 Slide
                final_frame, is_cropped, crop_info = detect_and_crop_slide(original_frame)
                
                if is_cropped:
                    print(f"  [Auto-Crop] Slide {idx}: {crop_info}")
                
                timestamp = idx / self.fps
                minutes = int(timestamp / 60)
                seconds = timestamp % 60
                
                filename = f"slide_{len(saved_files)+1:03d}_t{minutes}m{seconds:.1f}s_g{gid:02d}_h{phash[:8]}.jpg"
                filepath = os.path.join(self.output_folder, filename)
                
                cv2.imwrite(filepath, final_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_files.append(filepath)
                
                self.metadata.append({
                    'index': len(saved_files),
                    'filename': filename,
                    'frame_index': idx,
                    'timestamp': timestamp,
                    'phash': phash,
                    'group_id': gid,
                    'is_cropped': is_cropped
                })
                
            # 保存元數據
            metadata_path = os.path.join(self.output_folder, 'slides_metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'video_path': self.video_path,
                    'total_frames': self.total_frames,
                    'fps': self.fps,
                    'threshold': self.threshold,
                    'slides': self.metadata,
                    'similarity_groups': {str(gid): [] for gid in range(group_id)} # 簡化結構
                }, f, indent=2, ensure_ascii=False)
                
        finally:
            cap.release()
            
        return saved_files



def capture_slides_improved(video_path: str, output_folder: str, threshold: float = 0.85, ultra_mode: bool = False, smart_mode: bool = False) -> Tuple[bool, Dict]:
    """改進的幻燈片捕獲函數接口"""
    # 設置 multiprocessing 啟動方法，這對 macOS 兼容性很重要
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass
        
    capturer = ImprovedSlideCapture(video_path, output_folder, threshold, ultra_mode, smart_mode)
    return capturer.multi_strategy_capture()


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Parallel Slide Capture Tool')
    parser.add_argument('video_path', help='Path to video file')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--threshold', '-t', type=float, default=0.85, help='Similarity threshold')
    parser.add_argument('--ultra', '-u', action='store_true', help='Enable Ultra mode (Dense scanning)')
    parser.add_argument('--smart', '-s', action='store_true', help='Enable Smart mode (Two-pass hybrid scanning)')
    
    args = parser.parse_args()
    
    video_file = args.video_path
    output_dir = args.output if args.output else f"slides_{os.path.splitext(os.path.basename(video_file))[0]}"
    
    print("使用改進的方法(並行版)捕獲幻燈片...")
    if args.ultra:
        print("🚀 ULTRA MODE ENABLED: 使用最高靈敏度與密度掃描")
    elif args.smart:
        print("🧠 SMART MODE ENABLED: 使用雙重混合掃描 (速度+完整性)")
        
    success, result = capture_slides_improved(video_file, output_dir, args.threshold, args.ultra, args.smart)
    
    if success:
        print(f"\n成功捕獲 {result['slide_count']} 張幻燈片")
        print(f"保存位置: {result['output_folder']}")
    else:
        print(f"\n捕獲失敗: {result.get('error', '未知錯誤')}")