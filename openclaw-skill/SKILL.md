---
name: audio_transcribe
description: >
  監控 Google Drive 或 inbox 資料夾中的新音訊/影片檔案，
  自動轉錄為文字、產生結構化摘要，並將結果回寫 Drive、
  發送 Telegram 通知。支援 GPT-4o 轉錄 + Gemini/GPT 摘要。
---

# Audio Transcribe & Summarize Skill

## 功能概覽

本 skill 提供完整的 **音訊 → 文字 → 摘要** 自動化流水線：

1. **監控資料夾** — 持續掃描 Google Drive Audio 資料夾與本機 inbox
2. **自動轉錄** — 使用 GPT-4o-transcribe 將音訊/影片轉為逐字稿
3. **AI 摘要** — 將逐字稿透過 Gemini 2.5 Pro 或 GPT-4o 產生結構化摘要
4. **結果分發** — 回寫 Google Drive、發送 Telegram 通知

## 使用方式

### Slash Command

```
/transcribe <音訊檔案路徑>          # 轉錄單一檔案
/transcribe-summarize <音訊檔案路徑> # 轉錄 + 摘要
/summarize <逐字稿檔案路徑>          # 僅摘要現有逐字稿
/inbox-watch                        # 啟動資料夾監控
/inbox-watch --stop                 # 停止監控
/inbox-watch --status               # 查看狀態
```

### 自然語言觸發

以下語句會觸發此 skill：
- 「幫我轉錄這個音訊」
- 「監控 audio 資料夾」
- 「把這段錄音轉成文字並摘要」
- 「開始 inbox watcher」
- 「這個 transcript 做個摘要」

## 執行步驟

### 轉錄（Transcribe）

1. 確認目標檔案存在且為支援格式（mp3, m4a, wav, mp4, mov 等）
2. 執行轉錄：
   ```bash
   cd ~/.openclaw/workspace/skills/audio-transcribe/scripts
   source venv/bin/activate
   python3 gpt4o_transcribe_clawbot.py "<檔案路徑>" \
     --language zh --format text --output "<輸出路徑>.txt"
   ```
3. 確認輸出檔案已產生

### 筆記整理（Summarize — 詳細筆記，非摘要）

轉錄完成後（或對現有逐字稿），執行筆記整理：

```bash
cd ~/.openclaw/workspace/skills/audio-transcribe/scripts
source venv/bin/activate

# 純逐字稿 → 詳細筆記
python3 summarize_transcript.py "<逐字稿.txt>" \
  --output "<輸出路徑>_detailed_notes.md" \
  --style medical

# 逐字稿 + slides 分析 → 二合一合併筆記
python3 summarize_transcript.py "<逐字稿.txt>" \
  --slides "<slides_analysis.md>" \
  --output "<輸出路徑>_merged_notes.md"
```

支援的 `--style` 選項：
- `medical` — 醫學演講詳細筆記（保留完整內容、修飾潤稿、階層重點化）
- `merged` — 演講者 + slides 二合一合併筆記（有 --slides 時自動啟用）
- `meeting` — 會議紀要（含 action items, decisions）
- `lecture` — 教學演講筆記（含學習重點、概念整理）
- `general` — 通用筆記

支援的 `--provider` 選項：
- `openai` — 使用 GPT-5.4（預設，1M context，128K output）
- `gemini` — 使用 Gemini 2.5 Pro（較便宜備選）

### 監控模式（Watch）

啟動持續監控：
```bash
~/.openclaw/workspace/skills/audio-transcribe/scripts/inbox_watcher.sh --daemon
```

監控來源：
1. Google Drive: `~/Library/CloudStorage/GoogleDrive-<你的帳號>/我的雲端硬碟/audio`
2. 本機 inbox: `~/inbox`

## 輸出格式

### 逐字稿（.txt）
純文字格式，保留完整內容。

### 詳細筆記（_detailed_notes.md / _merged_notes.md）
Markdown 格式，完整整理的演講筆記（非摘要）：
- 儘可能保留演講者完整內容，修飾潤稿
- **粗體**標示關鍵發現與數據
- *斜體*標示重要概念
- __底線__標示延伸解讀或 slides 補充
- 階層化組織，按主題/agenda 分段
- 合併模式：演講者為主軸，slides 延伸加強，不標 Sxx

## 環境需求

- Python 3.10+ with venv
- ffmpeg（音訊格式轉換）
- OpenAI API Key（轉錄 + GPT-5.4 筆記整理）
- Gemini API Key（備選 provider，可選）
- 網路連線

## 檔案結構

```
~/.openclaw/workspace/skills/audio-transcribe/
├── SKILL.md                          # 本檔案
└── scripts/
    ├── venv/                         # Python 虛擬環境
    ├── .env                          # API Keys
    ├── gpt4o_transcribe_clawbot.py   # 轉錄主程式
    ├── summarize_transcript.py       # 摘要主程式
    └── inbox_watcher.sh              # 資料夾監控
```
