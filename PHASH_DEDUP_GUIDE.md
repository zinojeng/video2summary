# 幻燈片感知哈希和去重功能指南

## 概述

本項目已經升級了幻燈片捕獲功能，添加了以下改進：

1. **感知哈希（pHash）**：使用更智能的圖像指紋技術
2. **相似幻燈片分組**：自動檢測和分組相似的幻燈片
3. **增強的文件命名**：包含時間戳和哈希信息
4. **元數據文件**：詳細記錄所有幻燈片信息

## 新的文件命名格式

### 標準格式
```
slide_001_t10.5s_h12345678.jpg
```
- `001`：幻燈片序號
- `t10.5s`：視頻中的時間戳（秒）
- `h12345678`：感知哈希的前8位

### 分組格式（用於相似幻燈片）
```
slide_g01_001_t10.5s_h12345678.jpg
```
- `g01`：相似組編號
- 其他部分同上

## 感知哈希的優勢

與傳統的MD5哈希相比，感知哈希（pHash）具有以下優勢：

1. **容錯性**：即使圖片有輕微變化（如壓縮、調整亮度），仍能識別為相似
2. **相似度計算**：可以計算兩張圖片的相似程度（0-100%）
3. **更適合視頻處理**：能處理視頻編碼導致的輕微差異

## 元數據文件

每次捕獲幻燈片後，會在輸出文件夾中生成 `slides_metadata.json`：

```json
{
  "video_path": "/path/to/video.mp4",
  "total_frames": 3000,
  "fps": 30.0,
  "threshold": 0.85,
  "slides": [
    {
      "index": 1,
      "filename": "slide_001_t5.0s_h12345678.jpg",
      "frame_index": 150,
      "timestamp": 5.0,
      "phash": "1234567890abcdef",
      "group_id": -1,
      "similar_frames": []
    }
  ],
  "similarity_groups": {
    "1": [[280, "hash1"], [300, "hash2"]]
  }
}
```

## 使用場景

### 1. 處理包含動畫的演示視頻

當演示中有逐步顯示的動畫時，新功能會：
- 檢測所有動畫幀
- 將它們分組到同一個相似組
- 只保存最清晰的一幀作為代表

### 2. 處理錄製質量不穩定的視頻

當視頻有亮度變化或輕微模糊時：
- 感知哈希能識別這些是同一張幻燈片
- 避免保存重複內容

### 3. 後期處理和整理

利用元數據文件，可以：
- 快速定位特定時間點的幻燈片
- 分析幻燈片的分佈情況
- 進行批量重命名或分類

## 在代碼中使用

### 標準模式（已更新）
```python
from video_audio_processor import capture_slides_from_video

success, result = capture_slides_from_video(
    "video.mp4",
    output_folder="slides",
    similarity_threshold=0.85,
    enable_metadata=True  # 新參數
)
```

### 改進模式（推薦）
```python
from improved_slide_capture import capture_slides_improved

success, result = capture_slides_improved(
    "video.mp4",
    output_folder="slides",
    threshold=0.85
)
```

## 調試和測試

運行測試腳本查看功能演示：
```bash
python test_phash_dedup.py
```

## 配置建議

1. **相似度閾值**：
   - 0.9-0.95：嚴格去重，只移除幾乎相同的幻燈片
   - 0.85-0.9：標準設置，平衡去重和保留
   - 0.8-0.85：寬鬆設置，可能保留更多變化

2. **何時關閉元數據**：
   - 處理大量視頻時，如果不需要詳細信息
   - 使用 `enable_metadata=False` 參數

## 未來改進方向

1. **智能分組命名**：根據內容特徵自動命名組
2. **並行處理**：加速哈希計算
3. **自動生成摘要**：基於分組信息生成幻燈片摘要
4. **相似度可視化**：生成相似度矩陣圖表