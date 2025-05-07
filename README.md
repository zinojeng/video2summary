# 視頻音頻處理工具 (Video Audio Processor)

這是一個強大的視頻和音頻處理工具，主要功能包括：

1. **音頻提取**：從視頻文件中提取音頻並保存為多種格式(mp3/wav/aac)
2. **幻燈片捕獲**：自動檢測視頻中的幻燈片變化並保存為圖片
3. **幻燈片處理**：將捕獲的幻燈片轉換為PowerPoint或Markdown文件

## 主要功能

### 音頻提取

- 從任何視頻格式中提取音頻
- 支持多種輸出格式：MP3、WAV、AAC
- 自定義輸出文件路徑和名稱

### 幻燈片捕獲

- 自動檢測視頻中的場景變化
- 可調整相似度閾值以控制捕獲靈敏度
- 保存所有檢測到的幻燈片為圖像文件

### 幻燈片處理

- 將捕獲的幻燈片轉換為PowerPoint演示文稿
- 生成Markdown文件，適合進一步編輯或發布
- 支持基本處理和使用MarkItDown進行增強處理

## 安裝說明

1. 確保您已安裝Python 3.8或更高版本
2. 克隆或下載此倉庫
3. 安裝依賴項：

```bash
pip install moviepy opencv-python numpy pillow python-pptx scikit-image
```

4. (可選) 安裝增強型Markdown生成功能：

```bash
pip install markitdown>=0.1.1
```

5. (可選) 安裝OpenAI庫以啟用AI輔助功能：

```bash
pip install openai
```

## 使用方法

運行程式：

```bash
python video_audio_processor.py
```

程式界面分為三個標籤頁，分別對應主要功能：

1. **音頻提取**：選擇視頻文件、設置輸出格式和路徑，然後點擊「提取音頻」按鈕
2. **幻燈片捕獲**：選擇視頻文件、設置輸出文件夾和相似度閾值，然後點擊「捕獲幻燈片」按鈕
3. **幻燈片處理**：選擇包含幻燈片圖片的文件夾，選擇輸出為PowerPoint或Markdown，然後點擊「處理幻燈片」按鈕

## 保存位置

- **音頻文件**：默認保存在原視頻相同位置，文件名為原視頻名加上音頻格式後綴
- **捕獲的幻燈片**：默認保存在名為"video_slides_{視頻名稱}"的文件夾中
- **PowerPoint文件**：默認保存為幻燈片文件夾名稱+.pptx
- **Markdown文件**：默認保存為幻燈片文件夾名稱+.md

## 依賴項目

- moviepy：處理視頻和音頻
- opencv-python & numpy：視頻幀分析和幻燈片捕獲
- pillow：圖像處理
- python-pptx：生成PowerPoint文件
- scikit-image：計算圖像相似度
- markitdown (可選)：增強型Markdown生成
- openai (可選)：AI輔助圖像分析和內容提取

## 開發說明

- `video_audio_processor.py`：主程式，提供GUI界面和主要功能
- `markitdown_helper.py`：輔助模組，處理圖像到Markdown和PowerPoint的轉換
- `test_slides.py`：測試腳本，用於測試幻燈片處理功能

## 常見問題

1. **幻燈片捕獲不完整**：調整相似度閾值，較低的值會捕獲更多的變化
2. **音頻提取失敗**：確保安裝了moviepy和其依賴項
3. **MarkItDown功能不可用**：確保安裝了markitdown模組（`pip install markitdown>=0.1.1`）
