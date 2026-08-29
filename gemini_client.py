"""gemini_client.py

Gemini 文字/多模態呼叫的共用入口，走新的 `google-genai` SDK。

為什麼有這個檔案：舊的 `google.generativeai` 已經停止支援（import 時會印
"All support for the google.generativeai package has ended"），而且不保證能
呼叫到現行模型。專案裡好幾個工具都用同一組模式：

    model = genai.GenerativeModel(name)
    response = model.generate_content(prompt)
    response.text

這裡提供 `GeminiTextModel`，介面刻意保持一樣，所以呼叫端只要改「怎麼建立
model 物件」，後面的 `generate_content(...)` / `.text` 都不用動。

注意（Gemini 3.x）：
- 不接受 temperature / top_p / top_k，送了會回 400。本模組預設不送這些參數；
  真的要送必須明確傳入，且只在確定該模型支援時才用。
- 轉錄請用 `gemini_transcribe`，那是另一套 interactions API。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Sequence

_UNSUPPORTED_SAMPLING = ("temperature", "top_p", "top_k")


def _load_sdk():
    try:
        from google import genai  # type: ignore[attr-defined]
        from google.genai import types  # type: ignore[attr-defined]
    except ImportError as exc:  # pragma: no cover - 取決於環境
        raise ImportError(
            "需要新版 Gemini SDK：pip install google-genai\n"
            "（注意這與已停止支援的 google-generativeai 是不同套件）"
        ) from exc
    return genai, types


def resolve_api_key(api_key: Optional[str] = None) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("請設定環境變數 GEMINI_API_KEY 或 GOOGLE_API_KEY")
    return key


def get_client(api_key: Optional[str] = None):
    """建立 google-genai 的 Client。"""
    genai, _ = _load_sdk()
    return genai.Client(api_key=resolve_api_key(api_key))


def normalize_model_name(model: str) -> str:
    """去掉舊 SDK 慣用的 `models/` 前綴。

    舊的 google.generativeai 需要 `models/gemini-x`；新的 SDK 直接吃
    `gemini-x`，帶著前綴反而可能對不上。
    """
    return model[len("models/"):] if model.startswith("models/") else model


class GeminiResponse:
    """包一層，讓回應長得跟舊 SDK 一樣（.text / .usage_metadata）。"""

    def __init__(self, raw: Any):
        self._raw = raw

    @property
    def text(self) -> str:
        return getattr(self._raw, "text", "") or ""

    @property
    def usage_metadata(self):
        return getattr(self._raw, "usage_metadata", None)

    @property
    def raw(self):
        return self._raw

    def __getattr__(self, item):
        return getattr(self._raw, item)


class GeminiTextModel:
    """`genai.GenerativeModel` 的替代品，底層改用 google-genai。

    介面與舊 SDK 相容的部分：
        model = GeminiTextModel("gemini-3.7-flash")
        response = model.generate_content(prompt)
        response.text
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        system_instruction: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
    ):
        self._genai, self._types = _load_sdk()
        self.model = normalize_model_name(model)
        self.client = self._genai.Client(api_key=resolve_api_key(api_key))
        self.system_instruction = system_instruction
        self.max_output_tokens = max_output_tokens

    def _build_config(self, overrides: Optional[dict] = None):
        params: dict[str, Any] = {}
        if self.system_instruction:
            params["system_instruction"] = self.system_instruction
        if self.max_output_tokens:
            params["max_output_tokens"] = self.max_output_tokens

        if overrides:
            dropped = [k for k in _UNSUPPORTED_SAMPLING if k in overrides]
            if dropped:
                # Gemini 3.x 會直接 400，靜靜丟掉比讓整批工作失敗好，
                # 但要講出來，否則使用者會以為參數有生效。
                print(f"[Warn] Gemini 3.x 不接受 {', '.join(dropped)}，已忽略")
            params.update({k: v for k, v in overrides.items()
                           if k not in _UNSUPPORTED_SAMPLING and v is not None})

        return self._types.GenerateContentConfig(**params) if params else None

    def generate_content(self, contents, generation_config: Optional[dict] = None,
                         **kwargs) -> GeminiResponse:
        """送出一次生成請求。

        contents 可以是字串、或字串與已上傳檔案混合的 list（多模態）。
        generation_config 保留舊介面的名稱，接受 dict。
        """
        overrides = dict(generation_config or {})
        overrides.update(kwargs)
        config = self._build_config(overrides)

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return GeminiResponse(response)

    def upload_file(self, file_path: str | Path):
        """上傳檔案供多模態輸入使用（對應舊的 genai.upload_file）。"""
        return self.client.files.upload(file=str(file_path))


def upload_file(file_path: str | Path, api_key: Optional[str] = None):
    """獨立的上傳函式，給不需要保留 model 物件的呼叫端。"""
    return get_client(api_key).files.upload(file=str(file_path))


def generate_text(
    prompt: str,
    model: str,
    api_key: Optional[str] = None,
    system_instruction: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
) -> str:
    """一次性文字生成，回傳純文字。"""
    text_model = GeminiTextModel(
        model,
        api_key=api_key,
        system_instruction=system_instruction,
        max_output_tokens=max_output_tokens,
    )
    return text_model.generate_content(prompt).text.strip()


__all__ = [
    "GeminiResponse",
    "GeminiTextModel",
    "generate_text",
    "get_client",
    "normalize_model_name",
    "resolve_api_key",
    "upload_file",
]
