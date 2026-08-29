"""model_config.py

專案用到的 AI 模型集中在這裡，依「用途」而不是依「檔案」定義。

改模型只要改這一個檔案。各工具請 import 這裡的常數當預設值，不要再
把模型字串寫死在自己的 argparse default 或函式簽章裡。

--------------------------------------------------------------------------
更新時的檢查方式（模型汰換很快，這份清單會過期）
--------------------------------------------------------------------------
OpenAI  : https://developers.openai.com/api/docs/models
Gemini  : https://ai.google.dev/gemini-api/docs/models

實際可用的模型以帳號能列出的為準，這比文件可靠：

    python -c "from openai import OpenAI; \
        print([m.id for m in OpenAI().models.list()])"

    python -c "from google import genai; \
        print([m.name for m in genai.Client().models.list()])"

--------------------------------------------------------------------------
已知的坑
--------------------------------------------------------------------------
- gemini-2.0-flash-exp 已經停用（shut down），舊程式碼裡若還留著會直接失敗。
- Gemini 3.x 系列不接受 temperature / top_p / top_k，送了會回 400。
  舊的 GenerationConfig(temperature=...) 呼叫要拿掉這些參數。
- 轉錄模型（gpt-transcribe、gemini-3.5-transcribe）不能拿來做
  文字生成；翻譯/摘要請用下面的文字模型。
"""

from __future__ import annotations

# ==========================================================================
# 轉錄（語音轉文字）
# ==========================================================================
# OpenAI 目前建議的檔案轉錄模型。gpt-4o-transcribe / gpt-4o-mini-transcribe
# 官方已標示為「現有整合可續用，但不建議新專案採用」。
OPENAI_TRANSCRIBE = "gpt-transcribe"

# 唯一同時提供講者標記與詞級時間戳的後端。需要真實時間戳一律用它，
# 專案已不再提供 whisper-1（中文品質太差）。
GEMINI_TRANSCRIBE = "gemini-3.5-transcribe"
TIMESTAMP_TRANSCRIBE = GEMINI_TRANSCRIBE

# ==========================================================================
# 長文生成：講者筆記、摘要、合併筆記
# ==========================================================================
# 需要吃下整場演講逐字稿並產出結構化筆記，重品質。
OPENAI_NOTES = "gpt-5.6-terra"
GEMINI_NOTES = "gemini-3.7-flash"

# 特別複雜的推理（跨講者比對、臨床判讀）才用旗艦，較貴。
OPENAI_REASONING = "gpt-5.6-sol"
GEMINI_REASONING = "gemini-3.1-pro-preview"

# ==========================================================================
# 影像理解：投影片分析
# ==========================================================================
# 批次跑幾百張投影片，重成本與吞吐量。
OPENAI_VISION = "gpt-5.6-luna"
GEMINI_VISION = "gemini-3.5-flash-lite"

# 投影片內容特別密（表格、統計圖）時改用這組。
OPENAI_VISION_HQ = "gpt-5.6-terra"
GEMINI_VISION_HQ = "gemini-3.7-flash"

# ==========================================================================
# 翻譯
# ==========================================================================
OPENAI_TRANSLATION = "gpt-5.6-terra"
GEMINI_TRANSLATION = "gemini-3.5-flash-lite"


# ==========================================================================
# 逐字稿潤飾 / 摘要（speech2text 的 transcript_refiner、summary）
# ==========================================================================
OPENAI_REFINE = "gpt-5.6-terra"
GEMINI_REFINE = "gemini-3.7-flash"

# 便宜、量大的潤飾（長逐字稿分段處理）
OPENAI_REFINE_CHEAP = "gpt-5.6-luna"
GEMINI_REFINE_CHEAP = "gemini-3.5-flash-lite"


# ==========================================================================
# 成本／品質分級：給 UI 讓使用者自己選，不要在程式裡替他決定
# ==========================================================================
TIER_ECONOMY = "經濟"
TIER_STANDARD = "標準"
TIER_QUALITY = "高品質"

MODEL_TIERS = {
    "OpenAI": {
        TIER_ECONOMY: OPENAI_REFINE_CHEAP,
        TIER_STANDARD: OPENAI_REFINE,
        TIER_QUALITY: OPENAI_REASONING,
    },
    "Gemini": {
        TIER_ECONOMY: GEMINI_REFINE_CHEAP,
        TIER_STANDARD: GEMINI_REFINE,
        TIER_QUALITY: GEMINI_REASONING,
    },
}

TIER_ORDER = (TIER_ECONOMY, TIER_STANDARD, TIER_QUALITY)


def tier_label(provider: str, tier: str) -> str:
    """UI 上顯示的分級說明，含模型名與每 1M tokens 價格。"""
    model = MODEL_TIERS[provider][tier]
    price = MODEL_PRICING.get(model)
    if not price:
        return f"{tier}（{model}）"
    return (f"{tier}（{model}）— 輸入 ${price['input']}/M、"
            f"輸出 ${price['output']}/M")


# ==========================================================================
# 價格表（USD per 1M tokens；轉錄為 USD per minute）
#
# 價格會變，並且會因為 context 長度分級。這裡記的是短 context 的標準價，
# 只作為 UI 上的成本估算，不是計費依據。
# https://developers.openai.com/api/docs/pricing
# https://ai.google.dev/gemini-api/docs/pricing
# ==========================================================================
MODEL_PRICING = {
    # OpenAI 文字
    "gpt-5.6-sol":   {"input": 4.00, "cached_input": 0.40, "output": 20.00},
    "gpt-5.6-terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00},
    "gpt-5.6-luna":  {"input": 0.20, "cached_input": 0.02, "output": 1.20},
    # Gemini 文字
    # 3.7 Flash 目前是促銷價（2026-12-31 前 $0.75/$3.75，之後回到 $1.50/$7.50）
    "gemini-3.7-flash":       {"input": 0.75, "cached_input": 0.00, "output": 3.75},
    "gemini-3.5-flash-lite":  {"input": 0.30, "cached_input": 0.00, "output": 2.50},
    "gemini-3.1-pro-preview": {"input": 2.00, "cached_input": 0.00, "output": 12.00},
}

# 轉錄模型以「每分鐘音訊」計價
TRANSCRIBE_PRICING_PER_MINUTE = {
    "gpt-transcribe": 0.0045,
    "gemini-3.5-transcribe": 0.005,  # 音訊 0.003 + 文字 0.002
}


# ==========================================================================
# 舊模型對照：沿用舊設定檔或舊指令的人自動升級
# ==========================================================================
LEGACY_MODEL_ALIASES = {
    # 已停用，留著必定失敗
    "gemini-2.0-flash-exp": GEMINI_VISION,
    "gemini-1.5-pro": GEMINI_NOTES,
    "gemini-1.5-flash": GEMINI_VISION,
    "gemini-2.5-pro-preview-06-05": GEMINI_NOTES,
    # 仍可用但已是舊世代
    "gemini-2.5-pro": GEMINI_NOTES,
    "gemini-2.5-flash": GEMINI_VISION,
    "gpt-4o": OPENAI_NOTES,
    "gpt-4o-mini": OPENAI_VISION,
    "gpt-5.4": OPENAI_NOTES,
    # speech2text 舊登錄表裡的退役 OpenAI 模型
    "o1-mini": OPENAI_REFINE_CHEAP,
    "o3-mini": OPENAI_REFINE_CHEAP,
    "o4-mini": OPENAI_REFINE_CHEAP,
    "o4-mini-transcribe": OPENAI_TRANSCRIBE,
    "whisper-1": GEMINI_TRANSCRIBE,
    "gpt-3.5-turbo": OPENAI_REFINE_CHEAP,
    "gpt-4": OPENAI_REFINE,
    "gpt-4-vision-preview": OPENAI_VISION,
    "gpt-4-turbo": OPENAI_REFINE,
    # 退役的 Gemini
    "gemini-2.0-flash": GEMINI_VISION,
    "gemini-3-pro-preview": GEMINI_REASONING,
    "gemini-3-flash-preview": GEMINI_NOTES,
    # 轉錄
    "gpt-4o-transcribe": OPENAI_TRANSCRIBE,
    "gpt-4o-mini-transcribe": OPENAI_TRANSCRIBE,
}


def upgrade_legacy_model(model: str | None, allow_legacy: bool = False) -> str | None:
    """把舊模型名稱換成現行對應的模型。

    allow_legacy=True 時原樣返回，供刻意要沿用舊模型的呼叫端使用。
    未知的模型名稱一律原樣返回，不會被亂改。
    """
    if not model or allow_legacy:
        return model
    return LEGACY_MODEL_ALIASES.get(model, model)


def is_openai_model(model: str | None) -> bool:
    return bool(model) and not str(model).lower().startswith(("gemini", "models/gemini"))


__all__ = [
    "GEMINI_NOTES",
    "GEMINI_REFINE",
    "GEMINI_REFINE_CHEAP",
    "MODEL_PRICING",
    "MODEL_TIERS",
    "TIER_ECONOMY",
    "TIER_ORDER",
    "TIER_QUALITY",
    "TIER_STANDARD",
    "tier_label",
    "OPENAI_REFINE",
    "OPENAI_REFINE_CHEAP",
    "TRANSCRIBE_PRICING_PER_MINUTE",
    "GEMINI_REASONING",
    "GEMINI_TRANSCRIBE",
    "GEMINI_TRANSLATION",
    "GEMINI_VISION",
    "GEMINI_VISION_HQ",
    "LEGACY_MODEL_ALIASES",
    "OPENAI_NOTES",
    "OPENAI_REASONING",
    "TIMESTAMP_TRANSCRIBE",
    "OPENAI_TRANSCRIBE",
    "OPENAI_TRANSLATION",
    "OPENAI_VISION",
    "OPENAI_VISION_HQ",
    "is_openai_model",
    "upgrade_legacy_model",
]
