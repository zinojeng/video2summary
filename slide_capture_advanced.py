#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
進階幻燈片捕獲模組
使用感知哈希和相似度分組來改善後處理體驗
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional, Set
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from skimage.metrics import structural_similarity as ssim
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib


@dataclass
class SlideInfo:
    """幻燈片信息數據類"""
    frame_idx: int
    timestamp: float
    phash: str
    dhash: str
    group_id: int
    subgroup_idx: int
    filename: str
    is_transition: bool = False
    similarity_to_prev: float = 0.0
    

class AdvancedSlideCapture:
    """進階幻燈片捕獲類"""
    
    def __init__(self, video_path: str, output_folder: str, 
                 similarity_threshold: float = 0.85,
                 group_threshold: float = 0.90):
        self.video_path = video_path
        self.output_folder = output_folder
        self.similarity_threshold = similarity_threshold
        self.group_threshold = group_threshold  # 用於分組的相似度閾值
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.slides_info: List[SlideInfo] = []
        self.phash_to_group: Dict[str, int] = {}
        self.current_group_id = 0
        
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def compute_phash(self, image: np.ndarray, hash_size: int = 8) -> str:
        """計算感知哈希（pHash）"""
        # 轉換為灰度圖
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # 縮放到 hash_size x hash_size
        resized = cv2.resize(gray, (hash_size * 4, hash_size * 4))
        
        # 計算 DCT
        dct = cv2.dct(np.float32(resized))
        
        # 只保留左上角的低頻部分
        dct_low = dct[:hash_size, :hash_size]
        
        # 計算平均值（除了 DC 分量）
        avg = (dct_low.sum() - dct_low[0, 0]) / (hash_size * hash_size - 1)
        
        # 生成哈希
        hash_bits = (dct_low > avg).flatten()
        
        # 轉換為十六進制字符串
        hash_str = ''.join(['1' if b else '0' for b in hash_bits])
        return hex(int(hash_str, 2))[2:].zfill(hash_size * 2)
    
    def compute_dhash(self, image: np.ndarray, hash_size: int = 8) -> str:
        """計算差異哈希（dHash）"""
        # 轉換為灰度圖
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # 縮放到 (hash_size+1) x hash_size
        resized = cv2.resize(gray, (hash_size + 1, hash_size))
        
        # 計算水平梯度
        diff = resized[:, 1:] > resized[:, :-1]
        
        # 轉換為十六進制字符串
        hash_bits = diff.flatten()
        hash_str = ''.join(['1' if b else '0' for b in hash_bits])
        return hex(int(hash_str, 2))[2:].zfill(hash_size * 2)
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """計算兩個哈希之間的漢明距離"""
        # 轉換為二進制
        bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
        bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
        
        # 計算不同位的數量
        return sum(c1 != c2 for c1, c2 in zip(bin1, bin2))
    
    def hash_similarity(self, hash1: str, hash2: str) -> float:
        """計算兩個哈希的相似度（0-1）"""
        distance = self.hamming_distance(hash1, hash2)
        max_distance = len(hash1) * 4  # 每個十六進制字符 = 4 位
        return 1.0 - (distance / max_distance)
    
    def find_or_create_group(self, phash: str, dhash: str) -> Tuple[int, int]:
        """根據哈希找到或創建組"""
        best_group = -1
        best_similarity = 0.0
        
        # 查找最相似的組
        for existing_hash, group_id in self.phash_to_group.items():
            # 計算感知哈希相似度
            p_similarity = self.hash_similarity(phash, existing_hash)
            
            if p_similarity > best_similarity and p_similarity >= self.group_threshold:
                best_similarity = p_similarity
                best_group = group_id
        
        # 如果找到相似的組
        if best_group != -1:
            # 計算該組中的子索引
            group_slides = [s for s in self.slides_info if s.group_id == best_group]
            subgroup_idx = len(group_slides) + 1
            return best_group, subgroup_idx
        
        # 創建新組
        self.current_group_id += 1
        self.phash_to_group[phash] = self.current_group_id
        return self.current_group_id, 1
    
    def advanced_capture(self) -> Tuple[bool, Dict]:
        """使用進階方法捕獲幻燈片"""
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            
            print(f"開始分析視頻：{self.video_path}")
            print(f"總幀數：{self.total_frames}, FPS：{self.fps}")
            print(f"相似度閾值：{self.similarity_threshold}, 分組閾值：{self.group_threshold}")
            
            # 第一遍：快速掃描，找出可能的變化點
            print("\n第一遍：快速掃描...")
            candidate_frames = self.fast_scan()
            
            # 第二遍：精確檢測並計算哈希
            print(f"\n第二遍：精確檢測 {len(candidate_frames)} 個候選點...")
            slide_frames = self.precise_detection_with_hashing(candidate_frames)
            
            # 第三遍：分組和去重
            print("\n第三遍：分組和去重...")
            final_slides = self.group_and_deduplicate(slide_frames)
            
            # 保存幻燈片
            print(f"\n保存 {len(final_slides)} 張幻燈片...")
            saved_files = self.save_slides_with_grouping(final_slides)
            
            # 保存元數據
            self.save_metadata()
            
            # 生成統計信息
            stats = self.generate_statistics()
            
            return True, {
                "output_folder": self.output_folder,
                "slide_count": len(saved_files),
                "group_count": self.current_group_id,
                "saved_files": saved_files,
                "metadata_file": os.path.join(self.output_folder, "slides_metadata.json"),
                "statistics": stats
            }
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def fast_scan(self, step: int = 30) -> List[int]:
        """快速掃描找出變化點"""
        candidate_frames = []
        prev_frame = None
        
        # 動態調整步長
        if self.total_frames > 10000:
            step = 60
        elif self.total_frames > 5000:
            step = 45
        
        for i in range(0, self.total_frames, step):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            # 縮小圖片以加快處理
            small_frame = cv2.resize(frame, (320, 240))
            
            if prev_frame is not None:
                # 使用多種快速檢測方法
                hist_similarity = self.calculate_histogram_diff(prev_frame, small_frame)
                
                if hist_similarity < 0.95:
                    # 添加變化點前後的幀
                    for offset in range(-step//2, step//2 + 1, 5):
                        candidate_frame = i + offset
                        if 0 <= candidate_frame < self.total_frames:
                            candidate_frames.append(candidate_frame)
            
            prev_frame = small_frame
            
            if i % (step * 10) == 0:
                progress = (i / self.total_frames) * 100
                print(f"快速掃描進度：{progress:.1f}%")
        
        # 去重並排序
        candidate_frames = sorted(list(set(candidate_frames)))
        return candidate_frames
    
    def calculate_histogram_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """計算直方圖相似度"""
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    
    def precise_detection_with_hashing(self, candidate_frames: List[int]) -> List[Tuple[int, np.ndarray, str, str]]:
        """精確檢測並計算哈希"""
        slide_frames = []
        prev_frame = None
        prev_frame_idx = -1
        
        for idx, frame_idx in enumerate(candidate_frames):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
            
            # 計算哈希
            phash = self.compute_phash(frame)
            dhash = self.compute_dhash(frame)
            
            is_new_slide = False
            similarity = 0.0
            
            if prev_frame is None:
                is_new_slide = True
            else:
                # 計算 SSIM
                similarity = ssim(
                    cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                )
                
                if similarity < self.similarity_threshold:
                    is_new_slide = True
            
            if is_new_slide and (frame_idx - prev_frame_idx) > self.fps * 0.5:  # 至少間隔0.5秒
                slide_frames.append((frame_idx, frame.copy(), phash, dhash))
                prev_frame = frame
                prev_frame_idx = frame_idx
            
            if idx % 50 == 0:
                progress = (idx / len(candidate_frames)) * 100
                print(f"精確檢測進度：{progress:.1f}%")
        
        return slide_frames
    
    def group_and_deduplicate(self, slide_frames: List[Tuple[int, np.ndarray, str, str]]) -> List[Tuple[int, np.ndarray, SlideInfo]]:
        """分組並去重"""
        final_slides = []
        processed_hashes: Set[str] = set()
        
        for frame_idx, frame, phash, dhash in slide_frames:
            # 檢查是否已處理過非常相似的幻燈片
            skip = False
            for processed_hash in processed_hashes:
                if self.hash_similarity(phash, processed_hash) > 0.98:  # 幾乎相同
                    skip = True
                    break
            
            if skip:
                continue
            
            # 找到或創建組
            group_id, subgroup_idx = self.find_or_create_group(phash, dhash)
            
            # 創建幻燈片信息
            timestamp = frame_idx / self.fps
            slide_info = SlideInfo(
                frame_idx=frame_idx,
                timestamp=timestamp,
                phash=phash,
                dhash=dhash,
                group_id=group_id,
                subgroup_idx=subgroup_idx,
                filename="",  # 稍後填充
                is_transition=False,
                similarity_to_prev=0.0
            )
            
            self.slides_info.append(slide_info)
            final_slides.append((frame_idx, frame, slide_info))
            processed_hashes.add(phash)
        
        return final_slides
    
    def save_slides_with_grouping(self, slides: List[Tuple[int, np.ndarray, SlideInfo]]) -> List[str]:
        """保存幻燈片，使用分組命名"""
        saved_files = []
        
        for idx, (frame_idx, frame, slide_info) in enumerate(slides):
            # 生成文件名：slide_g01-02_t10.5s_h1a2b3c.jpg
            # g01-02 表示第1組第2張
            timestamp = slide_info.timestamp
            phash_short = slide_info.phash[:8]
            
            if slide_info.subgroup_idx > 1:
                # 相似幻燈片使用組號-子號格式
                filename = f"slide_g{slide_info.group_id:02d}-{slide_info.subgroup_idx:02d}_t{timestamp:.1f}s_{phash_short}.jpg"
            else:
                # 第一張幻燈片只用組號
                filename = f"slide_g{slide_info.group_id:02d}_t{timestamp:.1f}s_{phash_short}.jpg"
            
            filepath = os.path.join(self.output_folder, filename)
            slide_info.filename = filename
            
            # 保存圖片
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_files.append(filepath)
            
            print(f"保存幻燈片 {idx+1}/{len(slides)}: {filename}")
        
        return saved_files
    
    def save_metadata(self):
        """保存元數據到 JSON 文件"""
        metadata = {
            "video_info": {
                "path": self.video_path,
                "total_frames": self.total_frames,
                "fps": self.fps,
                "duration": self.total_frames / self.fps
            },
            "capture_settings": {
                "similarity_threshold": self.similarity_threshold,
                "group_threshold": self.group_threshold,
                "capture_time": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "slides": [asdict(slide) for slide in self.slides_info],
            "groups": self._generate_groups_summary()
        }
        
        metadata_path = os.path.join(self.output_folder, "slides_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"\n元數據已保存到: {metadata_path}")
    
    def _generate_groups_summary(self) -> Dict[str, Dict]:
        """生成組摘要信息"""
        groups = defaultdict(list)
        
        for slide in self.slides_info:
            groups[slide.group_id].append({
                "filename": slide.filename,
                "timestamp": slide.timestamp,
                "subgroup_idx": slide.subgroup_idx
            })
        
        summary = {}
        for group_id, slides in groups.items():
            summary[f"group_{group_id}"] = {
                "slide_count": len(slides),
                "time_range": {
                    "start": min(s["timestamp"] for s in slides),
                    "end": max(s["timestamp"] for s in slides)
                },
                "slides": slides
            }
        
        return summary
    
    def generate_statistics(self) -> Dict:
        """生成統計信息"""
        stats = {
            "total_slides": len(self.slides_info),
            "total_groups": self.current_group_id,
            "average_slides_per_group": len(self.slides_info) / max(1, self.current_group_id),
            "groups_distribution": {}
        }
        
        # 統計每組的幻燈片數
        group_counts = defaultdict(int)
        for slide in self.slides_info:
            group_counts[slide.group_id] += 1
        
        stats["groups_distribution"] = dict(group_counts)
        
        return stats


def capture_slides_advanced(video_path: str, output_folder: str, 
                          similarity_threshold: float = 0.85,
                          group_threshold: float = 0.90) -> Tuple[bool, Dict]:
    """進階幻燈片捕獲函數接口"""
    capturer = AdvancedSlideCapture(video_path, output_folder, 
                                   similarity_threshold, group_threshold)
    return capturer.advanced_capture()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python slide_capture_advanced.py <視頻文件路徑> [相似度閾值] [分組閾值]")
        sys.exit(1)
    
    video_file = sys.argv[1]
    similarity_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
    group_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.90
    
    output_dir = f"slides_advanced_{os.path.splitext(os.path.basename(video_file))[0]}"
    
    print("使用進階方法捕獲幻燈片...")
    print(f"相似度閾值: {similarity_threshold}")
    print(f"分組閾值: {group_threshold}")
    
    success, result = capture_slides_advanced(video_file, output_dir, 
                                            similarity_threshold, group_threshold)
    
    if success:
        print(f"\n成功捕獲 {result['slide_count']} 張幻燈片")
        print(f"分為 {result['group_count']} 組")
        print(f"保存位置: {result['output_folder']}")
        print(f"元數據文件: {result['metadata_file']}")
        
        # 顯示統計信息
        stats = result['statistics']
        print(f"\n統計信息:")
        print(f"- 平均每組幻燈片數: {stats['average_slides_per_group']:.1f}")
        print(f"- 各組分布: {stats['groups_distribution']}")
    else:
        print(f"\n捕獲失敗: {result.get('error', '未知錯誤')}")