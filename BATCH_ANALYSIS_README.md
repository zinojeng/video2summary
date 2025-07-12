# 批量幻燈片內容分析工具

這個工具可以批量使用 AI (OpenAI Vision API) 分析所有幻燈片文件夾中的圖片內容，自動生成包含文字提取和內容分析的 Markdown 文件。

## 功能特點

- 🔍 **自動發現**：自動查找所有 `*_slides` 文件夾
- 🤖 **AI 分析**：使用 OpenAI Vision API 提取和分析幻燈片內容
- 📝 **結構化輸出**：生成格式化的 Markdown 文件，包含：
  - 幻燈片圖片
  - 提取的文字內容
  - 圖表和表格描述
  - 視覺元素分析
- 🎯 **靈活選項**：
  - 分析所有幻燈片或只分析精選幻燈片
  - 支持跳過已分析的文件夾
  - 可強制重新分析
- 📊 **詳細報告**：生成處理統計和 JSON 報告

## 使用方法

### 1. 簡單方式（使用便捷腳本）

```bash
./run_batch_analysis.sh
```

腳本會引導您：
1. 輸入文件夾路徑（默認為 ADA2025）
2. 輸入 OpenAI API Key
3. 選擇處理模式
4. 選擇 AI 模型

### 2. 命令行方式

```bash
# 基本使用
python batch_slides_analysis.py "/Volumes/WD_BLACK/國際年會/ADA2025" --api-key YOUR_API_KEY

# 只分析精選幻燈片
python batch_slides_analysis.py "/Volumes/WD_BLACK/國際年會/ADA2025" --api-key YOUR_API_KEY --selected-only

# 使用 GPT-4 模型（更準確但較慢）
python batch_slides_analysis.py "/Volumes/WD_BLACK/國際年會/ADA2025" --api-key YOUR_API_KEY --model gpt-4o

# 強制重新分析（覆蓋現有分析）
python batch_slides_analysis.py "/Volumes/WD_BLACK/國際年會/ADA2025" --api-key YOUR_API_KEY --force
```

## 輸出文件

對於每個幻燈片文件夾，會生成：

1. **slides_analysis.md** - 所有幻燈片的完整分析
2. **selected_slides_analysis.md** - 精選幻燈片的分析（如果有 selected_slides 子文件夾）

每個分析文件包含：
- 標題和概述
- 每張幻燈片的圖片
- AI 提取的文字內容
- 結構化的內容分析

## 處理報告

完成後會生成 JSON 格式的處理報告：
- `batch_analysis_report_YYYYMMDD_HHMMSS.json`

包含：
- 處理統計
- 成功/失敗的文件夾列表
- API 調用次數
- 處理時間

## 注意事項

1. **API 費用**：每張圖片會調用一次 OpenAI Vision API，請注意費用
   - GPT-4o-mini：約 $0.003 每張圖片
   - GPT-4o：約 $0.01 每張圖片

2. **處理時間**：
   - 每張圖片約需 2-5 秒
   - 28 個文件夾完整分析可能需要 30-60 分鐘

3. **網絡要求**：需要穩定的網絡連接

## 故障排除

### 常見問題

1. **API Key 錯誤**
   - 確保使用正確的 OpenAI API Key
   - 檢查 API Key 是否有 Vision API 權限

2. **網絡超時**
   - 檢查網絡連接
   - 考慮使用 `--selected-only` 減少處理量

3. **記憶體不足**
   - 關閉其他應用程序
   - 分批處理文件夾

## 示例輸出

生成的 Markdown 文件示例：

```markdown
# 演講標題 - 完整幻燈片分析

## 幻燈片 1

![幻燈片 1](slide_g01_t3.0s_abc123.jpg)

### 標題
Introduction to Diabetes Management

### 主要內容
- Definition of diabetes
- Prevalence statistics
- Impact on public health

### 圖表描述
包含一個顯示糖尿病發病率趨勢的折線圖...

---
```

## 開發者信息

- 基於 `markitdown_helper.py` 模組
- 使用 OpenAI Vision API 進行圖片分析
- 支持批量處理和錯誤恢復