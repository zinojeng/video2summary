"""gemini_transcribe.py

Gemini 3.5 Transcribe 轉錄後端。

相對於 OpenAI 的 gpt-transcribe，這顆模型多了兩個本專案真正缺的能力：

1. **講者標記 (speaker diarization)** — 最多 8 位講者，會議/座談的講者筆記
   不必再靠人工分辨誰在講話。
2. **詞級時間戳** — OpenAI 這條路徑只有 whisper-1 有真時間戳（但中文品質
   較差），其餘模型的 SRT 時間軸都只能用字數估算。

另外 custom_vocabulary 可以放到 1000 個詞，對醫學會議的藥名與縮寫幫助很大。

注意事項：
- 需要新的 `google-genai` SDK（`pip install google-genai`），呼叫的是
  `client.interactions.create`，跟舊的 `google.generativeai` 完全不同。
- smart 模式與時間戳/diarization 互斥；要講者標記就必須用 verbatim。
- 實測（官方文件未載明）：custom_vocabulary 與 diarization、與詞級時間戳
  都互斥，三者只能擇一；且只開 diarization 而不開時間戳會拿到 0 筆標註，
  等於沒有講者標記，因為講者資訊是掛在 word 標註上的。
- 單次上限 1 小時；開了 diarization 或詞級時間戳則降為 30 分鐘。

文件：https://ai.google.dev/gemini-api/docs/transcribe
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

# 這顆模型的官方 id。live 版是串流用的，本模組只處理完整檔案。
GEMINI_TRANSCRIBE_MODEL = "gemini-3.5-transcribe"

# 開啟 diarization 或詞級時間戳時，單次請求的音訊長度上限（秒）。
MAX_SECONDS_WITH_ANNOTATIONS = 30 * 60
# 純轉錄（不要標記與時間戳）時的上限。
MAX_SECONDS_PLAIN = 60 * 60

# custom_vocabulary 的官方上限。
MAX_CUSTOM_VOCABULARY = 1000

# 本專案內部用的語言代碼 -> Gemini 官方文件列出的 BCP-47 代碼。
#
# 注意：官方支援清單裡的華語只有 cmn-Hans-CN（普通話）與
# yue-Hant-HK（粵語），沒有 zh-TW / zh-CN，送不在清單裡的代碼會被拒絕。
# 代碼名稱雖然帶 Hans，實測輸出仍是繁體；若某次拿到簡體，用
# --translate zh-tw 轉換。
# https://ai.google.dev/gemini-api/docs/transcribe#supported-languages
_LANGUAGE_CODE_MAP = {
    "zh": "cmn-Hans-CN",
    "zh-tw": "cmn-Hans-CN",
    "zh-hant": "cmn-Hans-CN",
    "zh-cn": "cmn-Hans-CN",
    "zh-hans": "cmn-Hans-CN",
    "cmn": "cmn-Hans-CN",
    "yue": "yue-Hant-HK",
    "zh-hk": "yue-Hant-HK",
    "en": "en-US",
    "ja": "ja-JP",
    "ko": "ko-KR",
}

# 送出這些語言時提醒使用者輸出可能是簡體。
_SIMPLIFIED_OUTPUT_HINT = {"zh", "zh-tw", "zh-hant"}

_AUDIO_MIME_TYPES = {
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}


def is_gemini_transcribe_model(model: Optional[str]) -> bool:
    """判斷是否要走本模組（gemini-3.5-transcribe 系列）。

    一般的 Gemini 文字/視覺模型走 gemini_client 的 generate_content，
    不在這裡處理。
    """
    return bool(model) and model.lower().startswith("gemini-3.5-transcribe")


def max_segment_seconds(diarization: bool = True, word_timestamps: bool = True) -> int:
    """回傳這組設定下單次請求可送的最長音訊秒數。"""
    if diarization or word_timestamps:
        return MAX_SECONDS_WITH_ANNOTATIONS
    return MAX_SECONDS_PLAIN


def to_bcp47(language: Optional[str]) -> list[str]:
    """把專案的語言代碼轉成 Gemini 的 language_codes。

    傳 None 或空字串會得到 []，也就是交給模型自動偵測。
    """
    if not language:
        return []
    normalized = language.strip().lower()
    if not normalized or normalized == "auto":
        return []
    if normalized in _SIMPLIFIED_OUTPUT_HINT:
        print("[Note] Gemini 的華語辨識代碼為 cmn-Hans-CN（官方清單無 zh-TW）；"
              "若輸出為簡體可加 --translate zh-tw 轉換")
    return [_LANGUAGE_CODE_MAP.get(normalized, language)]


def guess_mime_type(file_path: str | Path) -> str:
    return _AUDIO_MIME_TYPES.get(Path(file_path).suffix.lower(), "audio/mp3")


def _finite(value: float) -> Optional[float]:
    """擋掉 NaN / inf，避免產生無效的 SRT 時間碼。"""
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def parse_offset(value: Any) -> Optional[float]:
    """把各種可能的 offset 表示法轉成秒數（float）。

    SDK 在不同版本可能回傳 "1.234s" 字串、純數字、timedelta，或帶有
    seconds/nanos 的 Duration 物件，這裡一律吃下來。
    """
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _finite(float(value))

    # datetime.timedelta
    total_seconds = getattr(value, "total_seconds", None)
    if callable(total_seconds):
        try:
            return _finite(float(total_seconds()))
        except (TypeError, ValueError):
            return None

    # protobuf Duration 風格
    seconds = getattr(value, "seconds", None)
    if seconds is not None:
        nanos = getattr(value, "nanos", 0) or 0
        try:
            return _finite(float(seconds) + float(nanos) / 1e9)
        except (TypeError, ValueError):
            return None

    if isinstance(value, str):
        text = value.strip()
        if text.endswith("s"):
            text = text[:-1]
        try:
            return _finite(float(text))
        except ValueError:
            return None

    return None


def extract_word_annotations(interaction: Any) -> list[Any]:
    """從回應中取出 word_info 標註（可能為空）。"""
    words = []
    for step in getattr(interaction, "steps", None) or []:
        for content in getattr(step, "content", None) or []:
            for annotation in getattr(content, "annotations", None) or []:
                if getattr(annotation, "type", None) == "word_info":
                    words.append(annotation)
    return words


def group_words_into_segments(
    words: Iterable[Any],
    max_chars: int = 42,
    max_duration: float = 7.0,
    time_offset: float = 0.0,
) -> list[dict]:
    """把詞級標註聚合成字幕/筆記用的段落。

    切段規則（任一成立就換段）：
      1. 講者換人 —— 講者邊界永遠不合併，否則講者標記就沒意義了
      2. 這一段的字數超過 max_chars
      3. 這一段的長度超過 max_duration 秒

    time_offset 用於把分段檔案的相對時間還原成整份音訊的絕對時間。
    """
    segments: list[dict] = []
    current: Optional[dict] = None

    for word in words:
        text = (getattr(word, "text", "") or "").strip()
        start = parse_offset(getattr(word, "start_offset", None))
        end = parse_offset(getattr(word, "end_offset", None))
        speaker = getattr(word, "speaker", None) or None

        if not text:
            continue

        # 沒有時間資訊的詞（例如只開 diarization 沒開時間戳）仍要保留文字，
        # 但只有在講者相同時才能併入上一段，否則會把別人的話算到前一位講者頭上。
        if start is None or end is None:
            if current is not None and speaker == current["speaker"]:
                current["text"] = _join_text(current["text"], text)
            else:
                current = {
                    "start": None,
                    "end": None,
                    "text": text,
                    "speaker": speaker,
                }
                segments.append(current)
            continue

        start += time_offset
        end += time_offset
        # 模型偶爾會給出 end < start，夾成單點避免產生反向的 SRT 時間碼
        if end < start:
            end = start

        if current is None or current["start"] is None:
            # 沒有前一段，或前一段完全沒有時間資訊（無法延伸）
            should_start_new = True
        else:
            # 用實際合併後的長度判斷，_join_text 可能會插入一個空白
            merged_text = _join_text(current["text"], text)
            should_start_new = (
                speaker != current["speaker"]
                or len(merged_text) > max_chars
                or (end - current["start"]) > max_duration
            )

        if should_start_new:
            current = {
                "start": start,
                "end": end,
                "text": text,
                "speaker": speaker,
            }
            segments.append(current)
        else:
            current["text"] = merged_text
            # 時間戳不保證單調，取最大值避免 end 往回跳
            current["end"] = max(current["end"], end)

    return _fill_missing_times(segments)


def _fill_missing_times(segments: list[dict]) -> list[dict]:
    """替沒有時間資訊的段落，用前後鄰段補出一個時間窗。

    絕對不丟段落：這個函式的輸出同時餵給 segments_to_text（逐字稿）與
    normalize_timed_segments（SRT），丟掉任何一段都會讓逐字稿少字。
    補不出「有長度」的時間窗時就維持 start/end = None，之後只有 SRT
    那條路會把它濾掉。
    """
    if not segments:
        return []

    if all(seg["start"] is not None for seg in segments):
        return segments

    filled: list[dict] = []
    for index, seg in enumerate(segments):
        if seg["start"] is not None:
            filled.append(seg)
            continue

        prev_end = next(
            (s["end"] for s in reversed(segments[:index]) if s["end"] is not None), None
        )
        next_start = next(
            (s["start"] for s in segments[index + 1:] if s["start"] is not None), None
        )
        seg = dict(seg)
        # 只有在前後之間真的有空隙時才補；補不出正長度就留 None，
        # 文字仍會出現在逐字稿裡，只是不會有自己的字幕格。
        if (prev_end is not None and next_start is not None
                and next_start > prev_end):
            seg["start"] = prev_end
            seg["end"] = next_start
        filled.append(seg)

    return filled


def normalize_timed_segments(segments: Sequence[dict]) -> list[dict]:
    """把段落整理成可以直接產 SRT 的形式。

    1. 丟掉沒有時間或長度非正的段落（文字已另外保存在 text 裡）
    2. 依開始時間排序 —— 模型偶爾會給出亂序的標註，反向的時間碼會讓
       播放器整份字幕讀不出來
    """
    timed = [
        seg for seg in segments
        if seg.get("start") is not None
        and seg.get("end") is not None
        and seg["end"] > seg["start"]
    ]
    return sorted(timed, key=lambda seg: (seg["start"], seg["end"]))


def _join_text(existing: str, addition: str) -> str:
    """中文之間不加空白，其餘情況以空白相接。"""
    if not existing:
        return addition
    if _is_cjk(existing[-1]) or _is_cjk(addition[0]):
        return existing + addition
    return existing + " " + addition


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF      # CJK 統一漢字
        or 0x3400 <= code <= 0x4DBF   # 擴充 A
        or 0x3000 <= code <= 0x303F   # CJK 標點
        or 0xFF00 <= code <= 0xFFEF   # 全形標點
    )


def segments_to_text(segments: Sequence[dict], include_speakers: bool = True) -> str:
    """把段落組回純文字。有講者標記時以「講者換人」分段。"""
    if not segments:
        return ""

    if not include_speakers:
        merged = ""
        for seg in segments:
            merged = _join_text(merged, seg["text"])
        return merged

    lines: list[str] = []
    current_speaker = object()  # 哨兵，確保第一段一定會開新行
    buffer = ""

    for seg in segments:
        speaker = seg.get("speaker")

        # speaker 換人（None 也算一種「講者」，不能併進前一位的段落）
        if speaker != current_speaker:
            if buffer:
                lines.append(buffer)
            current_speaker = speaker
            prefix = f"[{speaker}] " if speaker is not None else ""
            buffer = prefix + seg["text"]
        else:
            buffer = _join_text(buffer, seg["text"])

    if buffer:
        lines.append(buffer)

    return "\n\n".join(lines)


class GeminiTranscriber:
    """gemini-3.5-transcribe 的檔案轉錄器。

    回傳格式刻意與 OpenAI 分支一致（dict 帶 'text' 與 'segments'），
    這樣 SRT 產生、翻譯、分段合併等既有管線都不必改。
    """

    def __init__(self, api_key: Optional[str] = None):
        try:
            from google import genai  # type: ignore[attr-defined]
        except ImportError as exc:  # pragma: no cover - 取決於環境
            raise ImportError(
                "使用 gemini-3.5-transcribe 需要新版 SDK：pip install google-genai\n"
                "（注意這與舊的 google-generativeai 是不同套件）"
            ) from exc

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("請設定環境變數 GEMINI_API_KEY 或 GOOGLE_API_KEY")

        self._genai = genai
        self.client = genai.Client(api_key=key)

    def build_transcription_config(
        self,
        language: Optional[str] = "zh",
        keywords: Optional[Sequence[str]] = None,
        diarization: bool = True,
        word_timestamps: bool = True,
    ) -> dict:
        """組出 transcription_config。

        smart 模式與 diarization/時間戳互斥，所以只要有任一項開啟就用
        verbatim；兩者都關才用 smart（讀起來較順、會自動加標點）。
        """
        config: dict[str, Any] = {"language_codes": to_bcp47(language)}

        # 實測得到的限制（官方文件沒寫）：
        #   - custom_vocabulary 與 diarization 互斥
        #   - custom_vocabulary 與 timestamps 互斥
        #   - 只開 diarization 不開 timestamps 會拿到 0 筆 word 標註，
        #     等於沒有講者標記；講者資訊是掛在 word 標註上的
        if diarization and not word_timestamps:
            print("[Note] 講者標記需要詞級時間戳才會有輸出，已一併開啟")
            word_timestamps = True

        wants_annotations = diarization or word_timestamps

        if keywords and wants_annotations:
            print(
                "[Warn] custom_vocabulary 無法與講者標記/詞級時間戳並用（API 限制），"
                "本次忽略 keywords。\n"
                "       若專有名詞比講者標記重要，請加 "
                "--no-diarization --no-word-timestamps"
            )
            keywords = None

        if keywords:
            vocabulary = [k.strip() for k in keywords if k and k.strip()]
            if len(vocabulary) > MAX_CUSTOM_VOCABULARY:
                print(
                    f"[Warn] custom_vocabulary 上限 {MAX_CUSTOM_VOCABULARY} 個詞，"
                    f"已截斷（原有 {len(vocabulary)} 個）"
                )
                vocabulary = vocabulary[:MAX_CUSTOM_VOCABULARY]
            if vocabulary:
                config["custom_vocabulary"] = vocabulary

        if wants_annotations:
            mode: dict[str, Any] = {"type": "verbatim"}
            if diarization:
                mode["diarization_mode"] = "speaker"
            if word_timestamps:
                mode["timestamp_granularities"] = ["word"]
            config["mode"] = mode
        else:
            config["mode"] = "smart"

        return config

    def transcribe_file(
        self,
        file_path: str | Path,
        language: Optional[str] = "zh",
        keywords: Optional[Sequence[str]] = None,
        diarization: bool = True,
        word_timestamps: bool = True,
        time_offset: float = 0.0,
        model: str = GEMINI_TRANSCRIBE_MODEL,
    ) -> dict:
        """轉錄單一音檔。

        回傳 {'text': str, 'segments': [{'start','end','text','speaker'}]}。
        沒有詞級標註時 segments 會是空 list，呼叫端就會退回估算時間軸。
        """
        file_path = str(file_path)

        # 超過幾秒的檔案官方建議先上傳再用 uri 引用，避免 inline 體積問題。
        uploaded = self.client.files.upload(file=file_path)
        audio_input = {
            "type": "audio",
            "uri": uploaded.uri,
            "mime_type": getattr(uploaded, "mime_type", None) or guess_mime_type(file_path),
        }

        transcription_config = self.build_transcription_config(
            language=language,
            keywords=keywords,
            diarization=diarization,
            word_timestamps=word_timestamps,
        )
        # build_transcription_config 可能會把 word_timestamps 補開，
        # 這裡以實際送出的 config 為準來判斷該不該期待標註。
        mode = transcription_config.get("mode")
        expects_annotations = isinstance(mode, dict)

        interaction = self.client.interactions.create(
            model=model,
            input=[audio_input],
            generation_config={"transcription_config": transcription_config},
        )

        words = extract_word_annotations(interaction)
        segments = group_words_into_segments(words, time_offset=time_offset)

        # 有講者/時間戳時用聚合結果（帶講者標記），否則用模型直接給的文字。
        if segments:
            text = segments_to_text(segments, include_speakers=diarization)
        else:
            text = getattr(interaction, "output_text", "") or ""
            if expects_annotations:
                print(
                    "[Warn] 回應中沒有 word_info 標註，"
                    "講者標記與詞級時間戳不可用（將退回估算時間軸）"
                )

        # 只把「有完整時間」的段落交出去：下游的 SRT 產生器會直接讀
        # start/end，含 None 會炸掉。文字已經保留在 text 裡，所以丟掉
        # 沒時間的段落不會遺失內容，只是那份 SRT 會退回估算時間軸。
        timed_segments = normalize_timed_segments(segments)
        if segments and not timed_segments:
            print("[Warn] 標註中沒有時間資訊，SRT 將退回估算時間軸")

        return {"text": text, "segments": timed_segments}


# 轉錄模型不能拿來做文字生成，翻譯時改用這顆文字模型。
from model_config import GEMINI_TRANSLATION as GEMINI_TEXT_MODEL


def generate_text(prompt: str, model: str = GEMINI_TEXT_MODEL,
                  api_key: Optional[str] = None) -> str:
    """用 Gemini 文字模型跑一次生成（翻譯用）。

    實作在 gemini_client，這裡只是保留既有呼叫端的入口。
    """
    from gemini_client import generate_text as _generate_text

    return _generate_text(prompt, model=model, api_key=api_key)


__all__ = [
    "GEMINI_TEXT_MODEL",
    "normalize_timed_segments",
    "generate_text",
    "GEMINI_TRANSCRIBE_MODEL",
    "GeminiTranscriber",
    "extract_word_annotations",
    "group_words_into_segments",
    "is_gemini_transcribe_model",
    "max_segment_seconds",
    "parse_offset",
    "segments_to_text",
    "to_bcp47",
]
