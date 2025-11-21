"""GPT-4o 語音轉文字工具函式。

此模組參考 `speech2text` 專案的 `audio2text/gpt4o_stt.py`
結構，並整合本專案的 `AudioTranscriber` 進階處理流程。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from gpt4o_transcribe_improved import AudioTranscriber


def transcribe_audio_gpt4o(
    file_path: str | Path,
    api_key: str,
    model: str = "gpt-4o-transcribe",
    language: Optional[str] = "zh",
    output_format: str = "text",
    auto_convert: bool = True,
    segment_duration: int = 600,
    request_timeout: int = 90,
) -> str:
    """使用 GPT-4o 模型轉錄音訊。

    參數與回傳值與 `speech2text` 專案保持一致，實作則
    復用本專案的 `AudioTranscriber` 以支援影片音軌擷取、
    大檔自動分段、格式轉換等進階功能。
    """

    transcriber = AudioTranscriber(api_key)
    return transcriber.transcribe(
        str(file_path),
        model=model,
        language=language or "zh",
        output_format=output_format,
        auto_convert=auto_convert,
        segment_duration=segment_duration,
        request_timeout=request_timeout,
    )


__all__ = ["transcribe_audio_gpt4o"]
