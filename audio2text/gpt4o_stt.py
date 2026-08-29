"""GPT-4o 語音轉文字工具函式。

此模組參考 `speech2text` 專案的 `audio2text/gpt4o_stt.py`
結構，並整合本專案的 `AudioTranscriber` 進階處理流程。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Sequence

from gpt4o_transcribe_improved import (
    AudioTranscriber,
    DEFAULT_TRANSCRIBE_MODEL,
    resolve_transcribe_model,
)


def transcribe_audio_gpt4o(
    file_path: str | Path,
    api_key: str,
    model: str = DEFAULT_TRANSCRIBE_MODEL,
    language: Optional[str] = "zh",
    output_format: str = "text",
    auto_convert: bool = True,
    segment_duration: Optional[int] = None,
    request_timeout: int = 90,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    keywords: Optional[Sequence[str]] = None,
    allow_legacy_model: bool = False,
    diarization: bool = True,
    word_timestamps: bool = True,
):
    """使用 GPT-4o 模型轉錄音訊。

    參數與回傳值與 `speech2text` 專案保持一致，實作則
    復用本專案的 `AudioTranscriber` 以支援影片音軌擷取、
    大檔自動分段、格式轉換等進階功能。

    progress_callback: 可選，接收 (status_message, fraction 0..1) 的回呼，
    供 GUI 顯示即時進度；長音檔分段時每段會有更新。

    keywords: 可選，音檔中可能出現的專有名詞（藥名、縮寫、講者名），
    僅新一代模型支援；舊模型會自動忽略。

    allow_legacy_model: True 時不把 gpt-4o-transcribe 等舊模型自動改寫。
    """

    model = resolve_transcribe_model(model, allow_legacy_model)
    transcriber = AudioTranscriber(api_key)
    return transcriber.transcribe(
        str(file_path),
        model=model,
        language=language or "zh",
        output_format=output_format,
        auto_convert=auto_convert,
        segment_duration=segment_duration,
        request_timeout=request_timeout,
        progress_callback=progress_callback,
        keywords=list(keywords) if keywords else None,
        diarization=diarization,
        word_timestamps=word_timestamps,
    )


__all__ = ["transcribe_audio_gpt4o"]
