#!/usr/bin/env python3
from __future__ import annotations

"""
Gmail Audio Processor — 監控 Gmail 收件匣的音訊附件
自動下載 → 轉錄 → 整理筆記 → 回信附上 .md + .docx

用法：
  python gmail_audio_processor.py                 # 掃描一次
  python gmail_audio_processor.py --daemon         # 持續監控
  python gmail_audio_processor.py --interval 60    # 60秒一輪
  python gmail_audio_processor.py --status         # 查看狀態
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import email
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime

# ===== 設定 =====
GMAIL_ACCOUNT = os.environ.get("GMAIL_ACCOUNT", "")
NOTIFY_TO = os.environ.get("NOTIFY_TO", "")
AUDIO_EXTENSIONS = {
    "mp3", "m4a", "wav", "ogg", "opus", "flac", "aac", "wma",
    "mp4", "mov", "mkv", "avi", "webm"
}
WORK_DIR = Path.home() / "inbox" / "gmail"
DONE_DIR = WORK_DIR / "done"
PROCESSED_FILE = WORK_DIR / ".gmail_processed"
POLL_INTERVAL = 60  # seconds

# Skill 路徑
SKILL_DIR = Path.home() / ".openclaw" / "workspace" / "skills" / "audio-transcribe" / "scripts"
PYTHON = SKILL_DIR / "venv" / "bin" / "python3"
TRANSCRIBER = SKILL_DIR / "gpt4o_transcribe_clawbot.py"
SUMMARIZER = SKILL_DIR / "summarize_transcript.py"

# Telegram
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def send_telegram(message: str):
    """發送 Telegram 通知（使用 urllib，避免 curl 編碼問題）"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    import urllib.request
    import urllib.parse
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            if '"ok":false' in body:
                log(f"  ⚠️ Telegram API 回傳錯誤: {body[:200]}")
    except Exception as e:
        log(f"  ⚠️ Telegram 發送失敗: {e}")


def run_gws(*args) -> dict | list | str | None:
    """執行 gws 指令並回傳 JSON 結果"""
    cmd = ["gws"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            log(f"  ⚠️ gws 錯誤: {result.stderr.strip()}")
            return None
        output = result.stdout.strip()
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output
    except subprocess.TimeoutExpired:
        log(f"  ⚠️ gws 逾時: {' '.join(cmd)}")
        return None
    except FileNotFoundError:
        log("  ❌ gws CLI 未安裝")
        return None


def setup_dirs():
    """建立工作目錄"""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.touch(exist_ok=True)


def is_processed(msg_id: str) -> bool:
    """檢查訊息是否已處理"""
    if PROCESSED_FILE.exists():
        return msg_id in PROCESSED_FILE.read_text()
    return False


def mark_processed(msg_id: str):
    """標記訊息已處理"""
    with open(PROCESSED_FILE, "a") as f:
        f.write(f"{msg_id}\n")


def get_unread_with_attachments() -> list[dict]:
    """查詢有附件或含 Drive 連結的未讀郵件"""
    all_messages = {}

    # 查詢 1: 有實體附件的未讀郵件
    result = run_gws(
        "gmail", "users", "messages", "list",
        "--params", json.dumps({
            "userId": "me",
            "q": "is:unread has:attachment",
            "maxResults": 10
        })
    )
    if result and "messages" in result:
        for m in result["messages"]:
            all_messages[m["id"]] = m

    # 查詢 2: 所有未讀郵件（涵蓋 Drive 連結、iCloud Mail Drop 等）
    # Gmail 全文搜尋不一定能匹配 URL，所以改用 is:unread 掃描全部，
    # 由 process_message() 中的 find_drive_links / find_icloud_links 在 Python 端過濾
    result2 = run_gws(
        "gmail", "users", "messages", "list",
        "--params", json.dumps({
            "userId": "me",
            "q": "is:unread",
            "maxResults": 10
        })
    )
    if result2 and "messages" in result2:
        for m in result2["messages"]:
            all_messages[m["id"]] = m

    return list(all_messages.values())


def get_message_detail(msg_id: str) -> dict | None:
    """取得郵件詳細資訊"""
    result = run_gws(
        "gmail", "users", "messages", "get",
        "--params", json.dumps({
            "userId": "me",
            "id": msg_id,
            "format": "full"
        })
    )
    return result


def extract_header(headers: list[dict], name: str) -> str:
    """從 headers 中擷取指定欄位"""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def find_audio_attachments(msg: dict) -> list[dict]:
    """找出郵件中的音訊附件"""
    attachments = []
    parts = msg.get("payload", {}).get("parts", [])
    if not parts:
        # 單一 part
        payload = msg.get("payload", {})
        filename = payload.get("filename", "")
        if filename and _is_audio(filename):
            attachments.append({
                "filename": filename,
                "attachmentId": payload.get("body", {}).get("attachmentId"),
                "mimeType": payload.get("mimeType", ""),
                "size": payload.get("body", {}).get("size", 0)
            })
        return attachments

    for part in parts:
        filename = part.get("filename", "")
        if filename and _is_audio(filename):
            attachments.append({
                "filename": filename,
                "attachmentId": part.get("body", {}).get("attachmentId"),
                "mimeType": part.get("mimeType", ""),
                "size": part.get("body", {}).get("size", 0)
            })
        # 遞迴檢查 nested parts
        for sub in part.get("parts", []):
            sf = sub.get("filename", "")
            if sf and _is_audio(sf):
                attachments.append({
                    "filename": sf,
                    "attachmentId": sub.get("body", {}).get("attachmentId"),
                    "mimeType": sub.get("mimeType", ""),
                    "size": sub.get("body", {}).get("size", 0)
                })
    return attachments


def _is_audio(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in AUDIO_EXTENSIONS


# ===== Google Drive 連結偵測 =====

# 音訊相關的 MIME type 前綴
AUDIO_MIME_PREFIXES = ("audio/", "video/")

# Google Drive 連結的 regex 模式
DRIVE_LINK_PATTERNS = [
    # https://drive.google.com/file/d/FILE_ID/view?...
    re.compile(r'https?://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)'),
    # https://drive.google.com/open?id=FILE_ID
    re.compile(r'https?://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'),
    # https://drive.google.com/uc?id=FILE_ID&...
    re.compile(r'https?://(?:docs|drive)\.google\.com/uc\?(?:.*&)?id=([a-zA-Z0-9_-]+)'),
    # https://drive.google.com/drive/folders/... (跳過資料夾)
    # 通用 id= 參數
    re.compile(r'https?://drive\.google\.com/.*[?&]id=([a-zA-Z0-9_-]+)'),
]

# iCloud Mail Drop 連結的 regex 模式
ICLOUD_LINK_PATTERNS = [
    re.compile(r'(https?://www\.icloud\.com/attachment/?\?u=[^\s"<>]+)'),
    re.compile(r'(https?://cvws\.icloud-content\.com/[^\s"<>]+)'),
]


def get_message_body(msg: dict) -> str:
    """從 Gmail API 訊息中擷取純文字 body"""
    parts = msg.get("payload", {}).get("parts", [])

    def _decode_body(body_data: str) -> str:
        """解碼 Gmail API 的 URL-safe base64 body"""
        if not body_data:
            return ""
        data = body_data.replace("-", "+").replace("_", "/")
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        try:
            return base64.b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _find_text_in_parts(parts_list: list) -> str:
        """遞迴搜尋 text/plain 或 text/html body"""
        text_plain = ""
        text_html = ""
        for part in parts_list:
            mime = part.get("mimeType", "")
            body_data = part.get("body", {}).get("data", "")
            if mime == "text/plain" and body_data:
                text_plain = _decode_body(body_data)
            elif mime == "text/html" and body_data:
                text_html = _decode_body(body_data)
            # 遞迴
            sub_parts = part.get("parts", [])
            if sub_parts:
                sub_text = _find_text_in_parts(sub_parts)
                if sub_text:
                    text_plain = text_plain or sub_text
        return text_plain or text_html

    if parts:
        return _find_text_in_parts(parts)

    # 單一 part（無 parts 陣列）
    payload = msg.get("payload", {})
    body_data = payload.get("body", {}).get("data", "")
    return _decode_body(body_data)


def find_drive_links(msg: dict) -> list[str]:
    """從信件 body 中擷取 Google Drive 檔案 ID"""
    body = get_message_body(msg)
    if not body:
        return []

    file_ids = []
    seen = set()
    for pattern in DRIVE_LINK_PATTERNS:
        for match in pattern.finditer(body):
            fid = match.group(1)
            if fid not in seen:
                seen.add(fid)
                file_ids.append(fid)

    if file_ids:
        log(f"  🔗 信件中找到 {len(file_ids)} 個 Google Drive 連結")

    return file_ids


def find_icloud_links(msg: dict) -> list[str]:
    """從信件 body 中擷取 iCloud Mail Drop 連結"""
    body = get_message_body(msg)
    if not body:
        return []

    urls = []
    seen = set()
    for pattern in ICLOUD_LINK_PATTERNS:
        for match in pattern.finditer(body):
            url = match.group(1)
            if url not in seen:
                seen.add(url)
                urls.append(url)

    if urls:
        log(f"  ☁️ 信件中找到 {len(urls)} 個 iCloud Mail Drop 連結")

    return urls


def download_icloud_file(url: str) -> Path | None:
    """從 iCloud Mail Drop 下載檔案"""
    try:
        # iCloud Mail Drop 會 redirect 到實際下載連結
        result = subprocess.run(
            ["curl", "-sL", "-D", "-", "-o", "/dev/null", "--max-redirs", "5", url],
            capture_output=True, text=True, timeout=30,
            stdin=subprocess.DEVNULL
        )
        # 從 headers 擷取檔名
        filename = None
        for line in result.stdout.splitlines():
            if "content-disposition" in line.lower() and "filename" in line.lower():
                m = re.search(r'filename[*]?=["\']?(?:UTF-8\'\')?([^"\';\r\n]+)', line)
                if m:
                    filename = m.group(1).strip()
                    # URL decode
                    from urllib.parse import unquote
                    filename = unquote(filename)

        if not filename:
            # 用 URL 的最後部分當檔名，或用預設名
            filename = f"icloud_attachment_{int(time.time())}.m4a"

        # 判斷是否為音訊/影片
        if not _is_audio(filename):
            log(f"  ⏭️ iCloud 檔案不是音訊/影片，跳過: {filename}")
            return None

        output_path = WORK_DIR / filename
        log(f"  ☁️ 下載 iCloud 檔案: {filename}")

        result = subprocess.run(
            ["curl", "-sL", "--max-redirs", "10", "-o", str(output_path), url],
            capture_output=True, text=True, timeout=600,
            stdin=subprocess.DEVNULL
        )

        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            size_mb = output_path.stat().st_size / 1024 / 1024
            log(f"  ✅ iCloud 檔案已下載: {filename} ({size_mb:.1f} MB)")
            return output_path
        else:
            log(f"  ❌ iCloud 下載失敗: {result.stderr[:200] if result.stderr else 'unknown'}")
            return None

    except subprocess.TimeoutExpired:
        log(f"  ❌ iCloud 下載逾時")
        return None
    except Exception as e:
        log(f"  ❌ iCloud 下載錯誤: {e}")
        return None


def download_drive_file(file_id: str) -> Path | None:
    """透過 gws 從 Google Drive 下載檔案（僅音訊/影片）"""
    # Step 1: 取得檔案資訊
    result = run_gws(
        "drive", "files", "get",
        "--params", json.dumps({
            "fileId": file_id,
            "fields": "name,mimeType,size"
        })
    )
    if not result or not isinstance(result, dict):
        log(f"  ⚠️ 無法取得 Drive 檔案資訊: {file_id}")
        return None

    filename = result.get("name", "")
    mime_type = result.get("mimeType", "")
    file_size = int(result.get("size", 0))

    log(f"  📁 Drive 檔案: {filename} ({mime_type}, {file_size / 1024 / 1024:.1f} MB)")

    # Step 2: 判斷是否為音訊/影片
    is_audio_mime = any(mime_type.startswith(p) for p in AUDIO_MIME_PREFIXES)
    is_audio_ext = _is_audio(filename) if filename else False

    if not is_audio_mime and not is_audio_ext:
        log(f"  ⏭️ Drive 檔案不是音訊/影片，跳過: {filename}")
        return None

    # Step 3: 下載檔案
    # gws drive files get --alt media 會存成 download.bin 並回傳 JSON 狀態
    save_path = WORK_DIR / filename
    cmd = [
        "gws", "drive", "files", "get",
        "--params", json.dumps({
            "fileId": file_id,
            "alt": "media"
        })
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            stdin=subprocess.DEVNULL,
            cwd=str(WORK_DIR)  # 在工作目錄執行，download.bin 會存在這裡
        )
        if result.returncode != 0:
            log(f"  ❌ Drive 下載失敗: {result.stderr[:200] if result.stderr else ''}")
            return None

        # 解析 gws 回傳的 JSON 狀態
        try:
            status = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            status = {}

        saved_file = status.get("saved_file", "download.bin")
        dl_status = status.get("status", "")
        dl_bytes = status.get("bytes", 0)

        # 找到下載的檔案
        downloaded = WORK_DIR / saved_file
        if not downloaded.exists():
            # 也檢查當前目錄
            downloaded = Path(saved_file)

        if dl_status == "success" and downloaded.exists():
            # 改名為正確的檔名
            downloaded.rename(save_path)
            log(f"  ✅ Drive 檔案已下載: {filename} ({dl_bytes / 1024 / 1024:.1f} MB)")
            return save_path
        else:
            log(f"  ❌ Drive 下載失敗: status={dl_status}, saved_file={saved_file}")
            return None

    except subprocess.TimeoutExpired:
        log(f"  ⚠️ Drive 下載逾時: {filename}")
        return None
    except Exception as e:
        log(f"  ❌ Drive 下載異常: {e}")
        return None


def download_attachment(msg_id: str, attachment_id: str, filename: str) -> Path | None:
    """下載 Gmail 附件"""
    result = run_gws(
        "gmail", "users", "messages", "attachments", "get",
        "--params", json.dumps({
            "userId": "me",
            "messageId": msg_id,
            "id": attachment_id
        })
    )
    if not result or "data" not in result:
        log(f"  ❌ 下載附件失敗: {filename}")
        return None

    # Gmail API 回傳 URL-safe base64
    data = result["data"]
    # 修正 URL-safe base64
    data = data.replace("-", "+").replace("_", "/")
    # 補齊 padding
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding

    try:
        raw_bytes = base64.b64decode(data)
    except Exception as e:
        log(f"  ❌ Base64 解碼失敗: {e}")
        return None

    save_path = WORK_DIR / filename
    save_path.write_bytes(raw_bytes)
    log(f"  ✅ 附件已下載: {filename} ({len(raw_bytes) / 1024 / 1024:.1f} MB)")
    return save_path


def transcribe_audio(audio_path: Path) -> Path | None:
    """轉錄音訊檔案"""
    stem = audio_path.stem
    output_file = WORK_DIR / f"{stem}.txt"

    log(f"  🎙️ 開始轉錄: {audio_path.name}")

    env = os.environ.copy()
    # 確保 PATH 包含 homebrew（背景模式下可能缺少）
    if "/opt/homebrew/bin" not in env.get("PATH", ""):
        env["PATH"] = f"/opt/homebrew/bin:{env.get('PATH', '/usr/bin:/bin')}"
    # 確保有 API key
    if "OPENAI_API_KEY" not in env:
        env_file = SKILL_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]  # 去掉 "export " 前綴
                if line.startswith("OPENAI_API_KEY="):
                    env["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

    result = subprocess.run(
        [str(PYTHON), str(TRANSCRIBER),
         str(audio_path),
         "--language", "zh",
         "--format", "text",
         "--output", str(output_file)],
        capture_output=True, text=True, timeout=3600,
        stdin=subprocess.DEVNULL,
        env=env, cwd=str(SKILL_DIR)
    )

    if result.returncode == 0 and output_file.exists():
        chars = len(output_file.read_text())
        log(f"  ✅ 轉錄完成: {stem}.txt ({chars} 字)")
        return output_file
    else:
        log(f"  ❌ 轉錄失敗: {result.stderr[-500:] if result.stderr else 'unknown error'}")
        return None


def summarize_transcript(transcript_path: Path) -> Path | None:
    """產生整理筆記"""
    stem = transcript_path.stem
    output_file = WORK_DIR / f"{stem}_detailed_notes.md"

    log(f"  📝 開始整理筆記: {stem}")

    env = os.environ.copy()
    # 確保 PATH 包含 homebrew（背景模式下可能缺少）
    if "/opt/homebrew/bin" not in env.get("PATH", ""):
        env["PATH"] = f"/opt/homebrew/bin:{env.get('PATH', '/usr/bin:/bin')}"
    if "OPENAI_API_KEY" not in env:
        env_file = SKILL_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]  # 去掉 "export " 前綴
                if line.startswith("OPENAI_API_KEY="):
                    env["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

    result = subprocess.run(
        [str(PYTHON), str(SUMMARIZER),
         str(transcript_path),
         "--provider", "openai",
         "--style", "medical",
         "--output", str(output_file)],
        capture_output=True, text=True, timeout=600,
        stdin=subprocess.DEVNULL,
        env=env, cwd=str(SKILL_DIR)
    )

    if result.returncode == 0 and output_file.exists():
        chars = len(output_file.read_text())
        log(f"  ✅ 筆記完成: {stem}_detailed_notes.md ({chars} 字)")
        return output_file
    else:
        log(f"  ❌ 筆記整理失敗: {result.stderr[-500:] if result.stderr else 'unknown error'}")
        return None


def convert_md_to_docx(md_path: Path) -> Path | None:
    """將 .md 轉成 .docx（優先用 docx-js，備援 pandoc）"""
    docx_path = md_path.with_suffix(".docx")

    # 方法1：使用 docx-js（專業排版、無書籤）
    converter_script = SKILL_DIR / "md_to_docx.js"
    if converter_script.exists():
        try:
            result = subprocess.run(
                ["/opt/homebrew/bin/node", str(converter_script), str(md_path), str(docx_path)],
                capture_output=True, text=True, timeout=120,
                stdin=subprocess.DEVNULL,
                env={**os.environ, "NODE_PATH": "/opt/homebrew/lib/node_modules"}
            )
            if result.returncode == 0 and docx_path.exists():
                log(f"  ✅ DOCX 轉換完成 (docx-js): {docx_path.name}")
                return docx_path
            else:
                log(f"  ⚠️ docx-js 轉換失敗: {result.stderr[:300] if result.stderr else 'unknown'}")
        except FileNotFoundError:
            log("  ⚠️ node 未安裝，嘗試 pandoc")

    # 方法2：備援 pandoc
    try:
        result = subprocess.run(
            ["pandoc", str(md_path), "-o", str(docx_path),
             "--from", "markdown", "--to", "docx"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and docx_path.exists():
            log(f"  ✅ DOCX 轉換完成 (pandoc): {docx_path.name}")
            return docx_path
    except FileNotFoundError:
        log("  ⚠️ pandoc 未安裝，跳過 DOCX 轉換")
        return None

    log(f"  ⚠️ DOCX 轉換失敗")
    return None


def send_reply_with_attachments(
    original_msg_id: str,
    thread_id: str,
    to_email: str,
    subject: str,
    body_text: str,
    attachments: list[Path]
):
    """回覆原始郵件並附上檔案"""
    # 建立 MIME 訊息
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["From"] = GMAIL_ACCOUNT
    msg["Subject"] = f"Re: {subject}"
    msg["In-Reply-To"] = original_msg_id
    msg["References"] = original_msg_id

    # 郵件正文
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # 附件（RFC 2231 編碼支援中文檔名）
    for filepath in attachments:
        if not filepath.exists():
            continue
        # 根據副檔名選擇 MIME 類型
        ext = filepath.suffix.lower()
        mime_map = {
            ".txt": ("text", "plain"),
            ".md": ("text", "markdown"),
            ".docx": ("application", "vnd.openxmlformats-officedocument.wordprocessingml.document"),
        }
        maintype, subtype = mime_map.get(ext, ("application", "octet-stream"))

        part = MIMEBase(maintype, subtype, name=filepath.name)
        part.set_payload(filepath.read_bytes())
        encoders.encode_base64(part)
        # RFC 2231 — 讓中文/非 ASCII 檔名正確顯示
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=("utf-8", "", filepath.name)
        )
        msg.attach(part)

    # 轉成 base64url
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    # 透過 gws 發送
    result = run_gws(
        "gmail", "users", "messages", "send",
        "--params", json.dumps({"userId": "me"}),
        "--json", json.dumps({
            "raw": raw,
            "threadId": thread_id
        })
    )

    if result and "id" in result:
        log(f"  📧 回信已發送 (thread: {thread_id})")
        return True
    else:
        log(f"  ⚠️ 回信發送失敗")
        return False


def mark_as_read(msg_id: str):
    """標記郵件為已讀"""
    run_gws(
        "gmail", "users", "messages", "modify",
        "--params", json.dumps({"userId": "me", "id": msg_id}),
        "--json", json.dumps({"removeLabelIds": ["UNREAD"]})
    )


def _process_audio_file(audio_path: Path) -> dict | None:
    """處理單一音訊檔：轉錄 → 筆記 → DOCX，回傳結果 dict"""
    filename = audio_path.name

    # Step 1: 轉錄
    transcript_path = transcribe_audio(audio_path)
    if not transcript_path:
        return None

    # Step 2: 整理筆記
    notes_path = summarize_transcript(transcript_path)

    # Step 3: 轉 DOCX
    docx_path = None
    if notes_path:
        docx_path = convert_md_to_docx(notes_path)

    # 移動已完成的音訊到 done
    try:
        done_path = DONE_DIR / filename
        audio_path.rename(done_path)
    except Exception:
        pass

    return {
        "filename": filename,
        "transcript": transcript_path,
        "notes_md": notes_path,
        "notes_docx": docx_path
    }


def process_message(msg_summary: dict):
    """處理一封含音訊附件或 Drive 連結的郵件"""
    msg_id = msg_summary["id"]

    if is_processed(msg_id):
        # 已處理過的郵件標為已讀，避免每次掃描都重複找到
        mark_as_read(msg_id)
        return

    log(f"📨 處理郵件 ID: {msg_id}")

    # 取得郵件詳情
    msg = get_message_detail(msg_id)
    if not msg:
        log(f"  ❌ 無法取得郵件詳情")
        return

    headers = msg.get("payload", {}).get("headers", [])
    from_email = extract_header(headers, "From")
    subject = extract_header(headers, "Subject")
    thread_id = msg.get("threadId", msg_id)
    message_id = extract_header(headers, "Message-ID")

    log(f"  From: {from_email}")
    log(f"  Subject: {subject}")

    # 找音訊附件（實體附件 + Drive 連結 + iCloud Mail Drop）
    audio_attachments = find_audio_attachments(msg)
    drive_file_ids = find_drive_links(msg)
    icloud_links = find_icloud_links(msg)

    if not audio_attachments and not drive_file_ids and not icloud_links:
        log(f"  ⏭️ 無音訊附件、Drive 連結或 iCloud 連結，跳過")
        mark_processed(msg_id)  # 避免重複檢查
        mark_as_read(msg_id)    # 標為已讀，下次不會再掃到
        return

    if audio_attachments:
        log(f"  🎵 找到 {len(audio_attachments)} 個音訊附件")
    if drive_file_ids:
        log(f"  🔗 找到 {len(drive_file_ids)} 個 Drive 連結待檢查")
    if icloud_links:
        log(f"  ☁️ 找到 {len(icloud_links)} 個 iCloud 連結待檢查")

    result_files = []

    # === Part A: 處理實體附件 ===
    for att in audio_attachments:
        filename = att["filename"]
        attachment_id = att["attachmentId"]

        if not attachment_id:
            log(f"  ⚠️ 附件 {filename} 沒有 attachmentId，跳過")
            continue

        audio_path = download_attachment(msg_id, attachment_id, filename)
        if not audio_path:
            continue

        rf = _process_audio_file(audio_path)
        if rf:
            result_files.append(rf)

    # === Part B: 處理 Google Drive 連結 ===
    for file_id in drive_file_ids:
        audio_path = download_drive_file(file_id)
        if not audio_path:
            continue

        rf = _process_audio_file(audio_path)
        if rf:
            result_files.append(rf)

    # === Part C: 處理 iCloud Mail Drop 連結 ===
    for icloud_url in icloud_links:
        audio_path = download_icloud_file(icloud_url)
        if not audio_path:
            continue

        rf = _process_audio_file(audio_path)
        if rf:
            result_files.append(rf)

    # Step 5: 回信
    if result_files:
        # 組裝回信內容（全繁體中文）
        body_lines = [
            f"您好，\n",
            f"您寄送的音訊檔案已完成轉錄與筆記整理，請參閱附件。\n"
        ]

        attachments_to_send = []

        for rf in result_files:
            body_lines.append(f"\n📎 原始檔案：{rf['filename']}")
            if rf["transcript"]:
                body_lines.append(f"  - 逐字稿：{rf['transcript'].name}")
            if rf["notes_md"]:
                body_lines.append(f"  - 整理筆記（Markdown）：{rf['notes_md'].name}")
                attachments_to_send.append(rf["notes_md"])
            if rf["notes_docx"]:
                body_lines.append(f"  - 整理筆記（Word）：{rf['notes_docx'].name}")
                attachments_to_send.append(rf["notes_docx"])

        # 也附上逐字稿
        for rf in result_files:
            if rf["transcript"]:
                attachments_to_send.append(rf["transcript"])

        body_lines.append(f"\n\n---\n🤖 由 OpenClaw 音訊處理管線自動產生")
        body_text = "\n".join(body_lines)

        # 擷取寄件人 email
        reply_to = from_email
        # 從 "Name <email>" 格式中擷取 email
        match = re.search(r'<(.+?)>', from_email)
        if match:
            reply_to = match.group(1)

        send_reply_with_attachments(
            original_msg_id=message_id or msg_id,
            thread_id=thread_id,
            to_email=reply_to,
            subject=subject,
            body_text=body_text,
            attachments=attachments_to_send
        )

        # 也寄一份到自己信箱（通知）
        if reply_to.lower() != NOTIFY_TO.lower():
            send_reply_with_attachments(
                original_msg_id=message_id or msg_id,
                thread_id=thread_id,
                to_email=NOTIFY_TO,
                subject=subject,
                body_text=f"[通知] 來自 {from_email} 的音訊已處理完成，已回覆原寄件者。\n\n{body_text}",
                attachments=attachments_to_send
            )

        # Telegram 通知
        file_names = ", ".join(rf["filename"] for rf in result_files)
        send_telegram(
            f"📧 *Gmail 音訊處理完成*\n"
            f"From: {from_email}\n"
            f"📎 {file_names}\n"
            f"📋 已回信附上逐字稿 + 整理筆記"
        )

    # 標記為已處理 + 已讀
    mark_processed(msg_id)
    mark_as_read(msg_id)


def scan_gmail():
    """掃描 Gmail 收件匣"""
    log("📬 掃描 Gmail 收件匣...")
    messages = get_unread_with_attachments()

    if not messages:
        log("  📭 無新郵件")
        return

    log(f"  📨 找到 {len(messages)} 封未讀郵件（含附件）")

    for msg_summary in messages:
        try:
            process_message(msg_summary)
        except Exception as e:
            log(f"  ❌ 處理失敗: {e}")
            import traceback
            traceback.print_exc()


def show_status():
    """顯示狀態"""
    print("===== Gmail Audio Processor =====")
    print(f"監控帳號: {GMAIL_ACCOUNT}")
    print(f"通知信箱: {NOTIFY_TO}")
    print(f"工作目錄: {WORK_DIR}")
    print(f"輪詢間隔: {POLL_INTERVAL}s")
    print()
    if PROCESSED_FILE.exists():
        count = len([l for l in PROCESSED_FILE.read_text().splitlines() if l.strip()])
        print(f"已處理郵件: {count} 封")
    if subprocess.run(["which", "gws"], capture_output=True).returncode == 0:
        print("gws CLI: ✅")
    else:
        print("gws CLI: ❌ 未安裝")
    if subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0:
        print("pandoc: ✅ (MD → DOCX)")
    else:
        print("pandoc: ⚠️ 未安裝（無法產生 .docx）")


def main():
    parser = argparse.ArgumentParser(description="Gmail Audio Processor")
    parser.add_argument("--daemon", action="store_true", help="持續監控模式")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL, help="輪詢間隔（秒）")
    parser.add_argument("--status", action="store_true", help="顯示狀態")
    parser.add_argument("--reset", action="store_true", help="清除處理記錄")
    args = parser.parse_args()

    if not GMAIL_ACCOUNT:
        print("錯誤：請設定環境變數 GMAIL_ACCOUNT（要監控的 Gmail 帳號）")
        sys.exit(1)

    if args.status:
        show_status()
        return

    if args.reset:
        if PROCESSED_FILE.exists():
            PROCESSED_FILE.unlink()
        print("已清除 Gmail 處理記錄")
        return

    setup_dirs()

    if args.daemon:
        log("🚀 Gmail Audio Processor 啟動（daemon 模式）")
        log(f"  帳號: {GMAIL_ACCOUNT}")
        log(f"  間隔: {args.interval}s")
        while True:
            try:
                scan_gmail()
            except Exception as e:
                log(f"❌ 掃描錯誤: {e}")
            time.sleep(args.interval)
    else:
        scan_gmail()


if __name__ == "__main__":
    main()
