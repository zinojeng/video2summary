#!/usr/bin/env python3
from __future__ import annotations
"""
summarize_transcript.py

將音訊逐字稿透過 AI 產生詳細筆記（非摘要）。
支援 Gemini 與 GPT 兩種 provider。

模式：
  1. transcript-only — 僅有逐字稿，產生完整整理筆記
  2. merged — 逐字稿 + slides 分析，合併為二合一筆記

用法：
    # 僅轉錄筆記
    python summarize_transcript.py transcript.txt

    # 合併筆記（transcript + slides）
    python summarize_transcript.py transcript.txt --slides slides_analysis.md

    # 指定風格與 provider
    python summarize_transcript.py transcript.txt --style medical --provider gemini
    python summarize_transcript.py transcript.txt --slides slides.md --style merged
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

from llm_provider_kit import GEMINI_NOTES, OPENAI_NOTES

# ---------------------------------------------------------------------------
# System prompts — 定義 AI 角色
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "medical": (
        "你是一位專業的醫學內容整理專家，專長於將醫學演講逐字稿"
        "轉化為結構清晰、保留完整細節的專業筆記。你不是做摘要，"
        "而是整理、修飾、潤稿演講者的完整內容。"
        "你的寫作風格以段落敘述為主，避免過度使用 bullet point，"
        "讓筆記像一篇經過專業編輯的醫學文章而非條列式清單。"
    ),
    "meeting": (
        "你是一位專業的會議紀錄整理專家，擅長將冗長的會議逐字稿"
        "轉化為結構清晰的會議筆記，保留所有決議和行動項目。"
    ),
    "lecture": (
        "你是一位專業的教學內容整理專家，擅長將學術演講逐字稿"
        "轉化為結構清晰的學習筆記，保留完整教學內容。"
    ),
    "general": (
        "你是一位專業的內容整理專家，擅長將逐字稿轉化為結構清晰的筆記。"
    ),
    "merged": (
        "內容分二部分，第一為演講者演講內容，第二為 Slides 內容。"
        "以「演講者的內容」為主軸，互相參照，用 slides 內容來加強"
        "演講者內容的述說或理解，或其中沒有講到的部分，增加論述。"
        "演講者提及與 Slides 合併在一起，另在下方延伸加強說明，不用重覆內容。"
        "作成合併演講者內容和 slides 更詳細內容的二合一筆記。"
        "不要用「演講者」與「Slides (Sxx)」標記，直接論述即可。"
        "儘可能保留演講者的內容，並作修飾潤稿，階層或重點化（粗體、底線、斜體）。"
        "寫作風格以段落敘述為主，避免過度使用 bullet point，"
        "讓筆記像一篇經過深度潤飾的專業醫學文章。"
    ),
}

# ---------------------------------------------------------------------------
# Prompt templates — 實戰迭代後的 prompt
# ---------------------------------------------------------------------------

PROMPTS = {
    # ======================================================================
    # transcript-only: 完整整理演講者內容（不是摘要！）
    # ======================================================================
    "medical": """請根據以下醫學演講逐字稿，整理成一份詳細的演講筆記。

## 核心原則
- 這不是「摘要」，是「整理演講者內容」——儘可能完整呈現演講者所說的內容
- 修飾潤稿，改善口語表達，但保留原意
- 重要術語保留英文原文（括號標注）
- 研究數據完整保留：研究名稱、n 值、endpoint、p-value、HR/OR 等

## 文體與格式規範（非常重要，請嚴格遵守）

### 以段落敘述為主體
- 筆記應該讀起來像一篇專業醫學文章，不是條列式清單
- 每個段落應包含完整的論述，用流暢的句子串聯
- 減少「教授提到」「教授強調」「教授指出」等重複性引導語

### Bullet point 使用限制
- 只在以下情況使用 bullet：(a) 需要逐項獨立說明、且每項超過一句話的內容；(b) 步驟性的治療流程或診斷流程
- 絕對禁止：把 3-8 個簡短詞彙（如檢查名稱、症狀名詞、鑑別診斷）拆成獨立 bullet
- 正確做法：短項目用逗號連接的 inline list。例如：「已做檢查包括 CBC、urinalysis、amylase、腹部超音波、胃鏡、大腸鏡等，結果大致正常。」
- 又例如：「常見誘發因子包括壓力、上呼吸道感染、手術、拔牙、外傷、劇烈活動及月經週期。」

### 標題層級
- 最多使用到 ###（三級標題），禁用 ####
- 每個章節要有足夠的內容量，避免只有 1-2 行就換新標題

### 病例呈現
- 病例用段落敘事呈現，像病歷摘要一樣流暢地講完
- 不要拆成「基本資料」「家族史」「檢查歷程」「檢查結果」等多個子標題配 bullet
- 正確做法：「38 歲男性，自 35 歲起反覆發作急性腹痛，每 1-2 個月一次，每次持續 2-5 天後自行緩解。伴隨噁心、嘔吐、腹瀉。三年間做遍 CBC、腹部超音波、CT、胃鏡、腸鏡等均無明確異常，僅 C3/C4 偏低...」

### 比較性內容用表格
- 疾病分型比較（如 Type 1/2/3）、藥物比較、鑑別診斷比較等，優先使用 Markdown 表格

### 重點標記
- **粗體**：關鍵發現、重要數據、藥物名稱
- *斜體*：英文醫學術語、概念名稱
- <u>底線</u>：臨床意義或延伸解析段落

### 延伸解析
- 在重要段落後，可加入 <u>底線標示的延伸解析</u>，針對機轉、臨床盲點與實務應用進行更深入的擴充說明
- 延伸解析的內容不重複原話，而是提供額外的臨床洞察

## 其他要求
- 使用繁體中文
- Markdown 格式
- 需要「完整、詳細、有層次」的筆記，不是精簡摘要
- Be as detailed as possible and as you can

逐字稿內容：
{transcript}""",

    "meeting": """請根據以下會議逐字稿，整理成一份詳細的會議筆記。

重要原則：
- 儘可能完整保留所有討論內容，不要遺漏
- 修飾潤稿，改善口語表達
- 按議題分段組織
- **粗體**標示重要決議、*斜體*標示待確認事項
- 行動項目用 checkbox 格式（- [ ]）
- 標註負責人和截止日期（如有提及）

格式：繁體中文、Markdown
Be as detailed as possible.

逐字稿內容：
{transcript}""",

    "lecture": """請根據以下教學演講逐字稿，整理成一份詳細的學習筆記。

重要原則：
- 完整保留演講者的教學內容，不是摘要
- 修飾潤稿，改善口語表達
- 按教學邏輯分段組織
- **粗體**標示核心概念、*斜體*標示定義、__底線__標示重要公式或引用
- 案例和範例完整保留
- 比較性內容用表格整理

格式：繁體中文、Markdown
Be as detailed as possible.

逐字稿內容：
{transcript}""",

    "general": """請根據以下逐字稿，整理成一份詳細的筆記。

重要原則：
- 儘可能完整保留原始內容
- 修飾潤稿，改善口語表達
- 階層化組織，使用清楚標題
- **粗體**標示重點、*斜體*標示補充說明

格式：繁體中文、Markdown
Be as detailed as possible.

逐字稿內容：
{transcript}""",

    # ======================================================================
    # merged: 演講者逐字稿 + Slides 分析 → 二合一筆記
    # ======================================================================
    "merged": """內容分二部分，第一為演講者演講內容，第二為 Slides 內容。

以「演講者的內容」為主軸，互相參照，用 slides 內容來加強演講者內容的述說或理解，或其中沒有講到的部分，增加論述。
演講者提及與 Slides 相關的內容合併在一起，另在下方延伸加強說明，不用重覆內容。
作成合併演講者內容和 slides 更詳細內容的二合一筆記。

## 合併原則
1. 不要用「演講者」與「Slides (Sxx)」這樣的標記，直接論述演講者即可
2. 儘可能保留演講者的內容，並作修飾潤稿，階層或重點化（**粗體**、<u>底線</u>、*斜體*）
3. 輔助說明也不用 Sxxx 等等，直接寫 slides 延伸說明
4. 以畫底線方式加入延伸解讀，或更清楚說明
5. 根據演講邏輯或使用者給予的 agenda 來分段整理
6. 不是 summary，是整理 speaker 內容——revised，但儘可能完整呈現
7. Need clear, detailed, comprehensive notes for what the speaker said

## 文體與格式規範（非常重要，請嚴格遵守）

### 以段落敘述為主體
- 筆記應該讀起來像一篇經過深度潤飾的專業醫學文章，不是條列式清單
- 每個段落應包含完整的論述，用流暢的句子串聯
- 減少「演講者提到」「講者強調」等重複性引導語，直接論述即可

### Bullet point 使用限制
- 只在以下情況使用 bullet：(a) 需要逐項獨立說明、且每項超過一句話的內容；(b) 步驟性的治療流程或診斷流程
- 絕對禁止：把 3-8 個簡短詞彙（如檢查名稱、症狀名詞、鑑別診斷）拆成獨立 bullet
- 正確做法：短項目用逗號連接的 inline list，寫在一句話裡

### 標題層級
- 最多使用到 ###（三級標題），禁用 ####
- 每個章節要有足夠的內容量，避免只有 1-2 行就換新標題

### 病例呈現
- 病例用段落敘事呈現，像病歷摘要一樣流暢地講完，不要拆成多個子標題配 bullet

### 比較性內容用表格
- 疾病分型比較、藥物比較、鑑別診斷比較等，優先使用 Markdown 表格

### 重點標記與延伸解析
- **粗體**：關鍵發現、重要數據、藥物名稱
- *斜體*：英文醫學術語、概念名稱
- <u>底線</u>：延伸解讀或臨床意義段落——增加論述的內容用底線標示
- 延伸解析不重複原話，而是提供額外的臨床洞察、機轉解說、實務應用

## 其他要求
- 使用繁體中文
- Markdown 格式
- Be the end. Sure you are as detailed as possible and as you can.

---

## 第一部分：演講者內容

{transcript}

---

## 第二部分：Slides 內容

{slides}""",
}

# ---------------------------------------------------------------------------
# Max token budget per chunk (rough char estimate)
# ---------------------------------------------------------------------------
MAX_CHARS = {
    "gemini": 800_000,   # Gemini 2.5/3.0 Pro ~1M tokens
    "openai": 800_000,   # GPT-5.4 1.05M context, 128K output
}


def load_env(env_path: str | None = None):
    """Load .env file if present."""
    paths_to_try = [
        env_path,
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.expanduser("~/.openclaw/workspace/skills/audio-transcribe/scripts/.env"),
    ]
    for p in paths_to_try:
        if p and os.path.isfile(p):
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        line = line.removeprefix("export ")
                        key, _, val = line.partition("=")
                        val = val.strip().strip('"').strip("'")
                        os.environ.setdefault(key.strip(), val)
            break


def read_file(path: str) -> str:
    """Read a text file with encoding detection."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到檔案：{path}")
    # Try UTF-8 first, fallback to other encodings
    for enc in ("utf-8", "utf-8-sig", "big5", "gbk", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"無法解碼檔案：{path}")


def build_prompt(style: str, transcript: str, slides: str | None = None) -> str:
    """Build the final prompt based on style and available inputs."""
    # If slides are provided and style is not explicitly merged,
    # auto-upgrade to merged style
    effective_style = style
    if slides and style != "merged":
        effective_style = "merged"
        print(f"[摘要] 偵測到 slides 輸入，自動切換為 merged 模式")

    if effective_style == "merged":
        if not slides:
            raise ValueError("merged 模式需要 --slides 參數提供投影片分析檔案")
        return PROMPTS["merged"].format(
            transcript=transcript,
            slides=slides,
        )
    else:
        return PROMPTS[effective_style].format(transcript=transcript)


def summarize_with_gemini(
    prompt: str,
    system_prompt: str,
    model: str = GEMINI_NOTES,
) -> str:
    """Summarize using Google Gemini API.

    走 gemini_client（新的 google-genai SDK）。舊的 google.generativeai 已停止
    支援，且 Gemini 3.x 不接受 temperature，所以這裡不再送取樣參數。
    """
    from llm_provider_kit import GeminiTextModel

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("未設定 GEMINI_API_KEY。請在 .env 或環境變數中設定。")

    model_obj = GeminiTextModel(
        model,
        api_key=api_key,
        system_instruction=system_prompt,
        max_output_tokens=65536,
    )

    return model_obj.generate_content(prompt).text


def summarize_with_openai(
    prompt: str,
    system_prompt: str,
    model: str = OPENAI_NOTES,
) -> str:
    """Summarize using OpenAI API (GPT-5.4 default).

    GPT-5.4 specs:
    - 1,050,000 context window
    - 128,000 max output tokens
    - Reasoning effort: none (default), low, medium, high, xhigh
    - Price: $2.50/M input, $15.00/M output
    """
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未設定 OPENAI_API_KEY。請在 .env 或環境變數中設定。")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_completion_tokens=65536,
    )

    return response.choices[0].message.content


def summarize(
    transcript_path: str,
    slides_path: str | None = None,
    output_path: str | None = None,
    provider: str = "openai",
    style: str = "medical",
    model: str | None = None,
) -> str:
    """Main summarization pipeline.

    Returns the path to the generated summary/notes file.
    """
    load_env()

    # Read inputs
    print(f"[筆記] 讀取逐字稿：{transcript_path}")
    transcript = read_file(transcript_path)
    print(f"[筆記] 逐字稿長度：{len(transcript):,} 字元")

    slides = None
    if slides_path:
        print(f"[筆記] 讀取 slides 分析：{slides_path}")
        slides = read_file(slides_path)
        print(f"[筆記] Slides 長度：{len(slides):,} 字元")

    if not transcript.strip():
        raise ValueError("逐字稿內容為空")

    # Auto-detect slides if not provided but file exists nearby
    if slides is None:
        # Look for slides analysis in common locations
        stem = Path(transcript_path).stem
        parent = Path(transcript_path).parent
        candidates = [
            parent / f"{stem}_slides" / "selected_slides_analysis.md",
            parent / f"{stem}_slides" / "slides_analysis.md",
            parent / "selected_slides_analysis.md",
        ]
        for c in candidates:
            if c.exists():
                print(f"[筆記] 自動偵測到 slides 分析：{c}")
                slides = read_file(str(c))
                slides_path = str(c)
                break

    # Determine effective style
    effective_style = style
    if slides and style not in ("merged",):
        effective_style = "merged"
        print(f"[筆記] 有 slides 輸入，自動升級為 merged 模式")

    # Trim inputs to fit provider limits
    max_chars = MAX_CHARS.get(provider, 400_000)
    if slides:
        # Split budget: 60% transcript, 40% slides
        t_budget = int(max_chars * 0.6)
        s_budget = int(max_chars * 0.4)
        transcript_trimmed = transcript[:t_budget]
        slides_trimmed = slides[:s_budget]
    else:
        transcript_trimmed = transcript[:max_chars]
        slides_trimmed = None

    # Build prompt
    prompt = build_prompt(effective_style, transcript_trimmed, slides_trimmed)
    system_prompt = SYSTEM_PROMPTS.get(effective_style, SYSTEM_PROMPTS["general"])

    # Determine output path
    if output_path is None:
        stem = Path(transcript_path).stem
        suffix = "_detailed_notes.md" if effective_style != "merged" else "_merged_notes.md"
        output_path = str(Path(transcript_path).parent / f"{stem}{suffix}")

    # Call AI
    default_models = {
        "gemini": GEMINI_NOTES,
        "openai": OPENAI_NOTES,
    }
    actual_model = model or default_models.get(provider, GEMINI_NOTES)
    print(f"[筆記] 使用 {provider} / {actual_model}，風格：{effective_style}")

    if provider == "gemini":
        result = summarize_with_gemini(prompt, system_prompt, model=actual_model)
    elif provider == "openai":
        result = summarize_with_openai(prompt, system_prompt, model=actual_model)
    else:
        raise ValueError(f"不支援的 provider：{provider}")

    # Add metadata header
    meta = {
        "source_transcript": Path(transcript_path).name,
        "source_slides": Path(slides_path).name if slides_path else None,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "provider": provider,
        "model": actual_model,
        "style": effective_style,
        "transcript_chars": len(transcript),
        "slides_chars": len(slides) if slides else 0,
    }
    # Filter None values
    meta = {k: v for k, v in meta.items() if v is not None}

    header_lines = ["---"]
    for k, v in meta.items():
        header_lines.append(f"{k}: {v}")
    header_lines.append("---\n\n")
    header = "\n".join(header_lines)

    full_output = header + result

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(full_output, encoding="utf-8")
    print(f"[筆記] ✓ 筆記已儲存：{output_path}")
    print(f"[筆記] 筆記長度：{len(result):,} 字元")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="將演講逐字稿整理為詳細筆記（非摘要），支援合併 slides 分析",
    )
    parser.add_argument(
        "transcript",
        help="逐字稿檔案路徑（.txt 或 .md）",
    )
    parser.add_argument(
        "--slides",
        help="投影片分析檔案路徑（.md），提供後自動啟用 merged 模式",
    )
    parser.add_argument(
        "--output", "-o",
        help="輸出路徑（預設：<原檔名>_detailed_notes.md 或 _merged_notes.md）",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["openai", "gemini"],
        default="openai",
        help=f"AI 模型供應商（預設：openai / {OPENAI_NOTES}）",
    )
    parser.add_argument(
        "--style", "-s",
        choices=list(PROMPTS.keys()),
        default="medical",
        help="筆記風格（預設：medical）；有 --slides 時自動切為 merged",
    )
    parser.add_argument(
        "--model", "-m",
        help=f"指定模型名稱（覆蓋預設）。例：{OPENAI_NOTES}, {GEMINI_NOTES}",
    )
    parser.add_argument(
        "--env",
        help=".env 檔案路徑",
    )

    args = parser.parse_args()

    if args.env:
        load_env(args.env)

    try:
        output = summarize(
            args.transcript,
            slides_path=args.slides,
            output_path=args.output,
            provider=args.provider,
            style=args.style,
            model=args.model,
        )
        print(f"\n✅ 完成！筆記檔案：{output}")
    except Exception as e:
        print(f"\n❌ 錯誤：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
