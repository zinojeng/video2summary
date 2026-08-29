#!/usr/bin/env python3
from __future__ import annotations

"""
tg_bot.py — Telegram Bot 接收訊息 + 音訊處理

功能：
  /status  — 查詢目前處理狀態（佇列、已完成數）
  /list    — 列出最近處理完成的檔案
  /rerun <名稱> — 重新處理指定檔案或資料夾
  /help    — 顯示可用指令

  傳送音訊檔 → 自動下載到 ~/audio/ → 觸發轉錄+筆記
  傳送圖片   → 提示使用者建立資料夾或加入現有資料夾

用法：
  python tg_bot.py                 # 前景執行
  python tg_bot.py --daemon        # 背景模式
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# ===== 設定 =====
AUDIO_DIR = Path.home() / "audio"
DONE_DIR = AUDIO_DIR / "done"
STATE_FILE = AUDIO_DIR / ".processor_state.json"

SKILL_DIR = Path.home() / ".openclaw" / "workspace" / "skills" / "audio-transcribe" / "scripts"

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

POLL_INTERVAL = 2  # seconds between getUpdates
OFFSET_FILE = AUDIO_DIR / ".tg_bot_offset"

AUDIO_EXTENSIONS = {
    "mp3", "m4a", "wav", "ogg", "opus", "flac", "aac", "wma",
    "mp4", "mov", "mkv", "avi", "webm"
}


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ===== Telegram API =====

def tg_api(method: str, data: dict = None, timeout: int = 30) -> dict:
    """呼叫 Telegram Bot API"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/{method}"
    if data:
        payload = urllib.parse.urlencode(data).encode("utf-8")
    else:
        payload = None
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"⚠️ Telegram API {method} 失敗: {e}")
        return {"ok": False, "error": str(e)}


def send_message(chat_id: str | int, text: str, parse_mode: str = "Markdown"):
    """發送文字訊息"""
    # Telegram Markdown 在某些字元上很挑剔，失敗時 fallback 到純文字
    result = tg_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    })
    if not result.get("ok") and parse_mode:
        # Markdown 解析失敗 → 改用純文字
        tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": text,
        })
    return result


def send_document(chat_id: str | int, file_path: Path, caption: str = ""):
    """發送檔案（使用 curl multipart/form-data）"""
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument",
        "-F", f"chat_id={chat_id}",
        "-F", f"document=@{file_path}",
    ]
    if caption:
        cmd += ["-F", f"caption={caption}"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120, text=True)
        resp = json.loads(result.stdout)
        if not resp.get("ok"):
            log(f"⚠️ sendDocument 失敗: {resp}")
        return resp
    except Exception as e:
        log(f"⚠️ sendDocument 錯誤: {e}")
        return {"ok": False}


def download_file(file_id: str, dest_path: Path) -> bool:
    """從 Telegram 下載檔案"""
    result = tg_api("getFile", {"file_id": file_id})
    if not result.get("ok"):
        log(f"⚠️ getFile 失敗: {result}")
        return False

    file_path = result["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}"

    try:
        urllib.request.urlretrieve(download_url, str(dest_path))
        log(f"  📥 下載完成: {dest_path.name} ({dest_path.stat().st_size / 1024:.1f} KB)")
        return True
    except Exception as e:
        log(f"⚠️ 下載失敗: {e}")
        return False


# ===== Offset 管理 =====

def load_offset() -> int:
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def save_offset(offset: int):
    OFFSET_FILE.write_text(str(offset))


# ===== State 讀取 =====

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"processed_folders": {}, "processed_audio": []}


# ===== 指令處理 =====

def cmd_help(chat_id):
    text = (
        "🤖 *音訊處理 Bot 指令*\n\n"
        "/status — 查詢處理狀態\n"
        "/list — 最近處理的檔案\n"
        "/rerun 名稱 — 重新處理指定檔案\n"
        "/pending — 待處理的檔案\n"
        "/help — 顯示本說明\n\n"
        "📎 直接傳送音訊檔 → 自動轉錄 + 筆記\n"
        "📎 傳送後回傳 .md + .docx 筆記檔"
    )
    send_message(chat_id, text)


def cmd_status(chat_id):
    state = load_state()
    n_folders = len(state.get("processed_folders", {}))
    n_audio = len(state.get("processed_audio", []))

    # 檢查 ~/audio/ 待處理
    pending_audio = []
    pending_folders = []
    if AUDIO_DIR.exists():
        for item in AUDIO_DIR.iterdir():
            if item.name.startswith(".") or item.name == "done":
                continue
            if item.is_file():
                ext = item.suffix.lstrip(".").lower()
                if ext in AUDIO_EXTENSIONS and str(item) not in state.get("processed_audio", []):
                    pending_audio.append(item.name)
            elif item.is_dir():
                folder_state = state.get("processed_folders", {}).get(item.name, {})
                if not folder_state.get("audio_done") or not folder_state.get("slides_done"):
                    pending_folders.append(item.name)

    # 檢查 daemons
    try:
        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        gmail_running = "gmail_audio_processor.py" in ps.stdout
        folder_running = "folder_processor.py --daemon" in ps.stdout
    except Exception:
        gmail_running = folder_running = False

    lines = [
        "📊 *處理狀態*\n",
        f"✅ 已處理音訊: {n_audio} 個",
        f"✅ 已處理資料夾: {n_folders} 個",
    ]

    if pending_audio:
        lines.append(f"\n⏳ 待處理音訊: {len(pending_audio)} 個")
        for name in pending_audio[:5]:
            lines.append(f"  • {name}")
    if pending_folders:
        lines.append(f"\n⏳ 待處理資料夾: {len(pending_folders)} 個")
        for name in pending_folders[:5]:
            lines.append(f"  • {name}")

    if not pending_audio and not pending_folders:
        lines.append("\n🎉 無待處理項目")

    lines.append(f"\n🔄 Gmail daemon: {'✅ 執行中' if gmail_running else '❌ 未執行'}")
    lines.append(f"📂 Folder daemon: {'✅ 執行中' if folder_running else '❌ 未執行'}")

    send_message(chat_id, "\n".join(lines))


def cmd_list(chat_id):
    state = load_state()

    lines = ["📋 *最近處理的檔案*\n"]

    # 已處理的音訊
    processed = state.get("processed_audio", [])
    if processed:
        lines.append("🎵 *音訊檔:*")
        for p in processed[-10:]:
            name = Path(p).name
            lines.append(f"  • {name}")

    # 已處理的資料夾
    folders = state.get("processed_folders", {})
    if folders:
        lines.append("\n📂 *資料夾:*")
        for fname, fstate in list(folders.items())[-10:]:
            status = []
            if fstate.get("audio_done"):
                status.append("🎙️")
            if fstate.get("slides_done"):
                status.append("🖼️")
            if fstate.get("merged"):
                status.append("📝")
            lines.append(f"  • {fname} {' '.join(status)}")

    if not processed and not folders:
        lines.append("（尚無處理記錄）")

    send_message(chat_id, "\n".join(lines))


def cmd_pending(chat_id):
    """列出待處理檔案"""
    state = load_state()
    pending = []

    if AUDIO_DIR.exists():
        for item in sorted(AUDIO_DIR.iterdir()):
            if item.name.startswith(".") or item.name == "done":
                continue
            if item.is_file():
                ext = item.suffix.lstrip(".").lower()
                if ext in AUDIO_EXTENSIONS and str(item) not in state.get("processed_audio", []):
                    pending.append(f"🎵 {item.name}")
            elif item.is_dir():
                fs = state.get("processed_folders", {}).get(item.name, {})
                if not fs.get("audio_done") or not fs.get("slides_done"):
                    n_files = len(list(item.iterdir()))
                    pending.append(f"📂 {item.name}/ ({n_files} 檔案)")

    if pending:
        text = "⏳ *待處理項目*\n\n" + "\n".join(pending)
    else:
        text = "🎉 目前沒有待處理的檔案"

    send_message(chat_id, text)


def cmd_rerun(chat_id, args: str):
    """重新處理指定檔案"""
    name = args.strip()
    if not name:
        send_message(chat_id, "⚠️ 用法: /rerun 檔案名稱\n例如: /rerun Pit-1")
        return

    state = load_state()

    # 檢查是否為資料夾
    folder = AUDIO_DIR / name
    if folder.is_dir():
        if name in state.get("processed_folders", {}):
            del state["processed_folders"][name]
            STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            send_message(chat_id, f"🔄 已重置 *{name}/*，下次掃描將重新處理")
        else:
            send_message(chat_id, f"📂 *{name}/* 尚未被處理過，將在下次掃描時處理")
        return

    # 檢查是否為音訊檔
    matched = None
    for p_str in state.get("processed_audio", []):
        p = Path(p_str)
        if p.stem == name or p.name == name:
            matched = p_str
            break

    if matched:
        state["processed_audio"].remove(matched)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

        # 如果在 done/ 裡，搬回 ~/audio/
        done_file = DONE_DIR / Path(matched).name
        if done_file.exists():
            dest = AUDIO_DIR / done_file.name
            done_file.rename(dest)
            send_message(chat_id, f"🔄 已將 *{done_file.name}* 搬回 ~/audio/，下次掃描將重新處理")
        else:
            send_message(chat_id, f"🔄 已重置 *{name}* 的處理記錄\n⚠️ 但找不到原始音訊檔，請重新放入 ~/audio/")
    else:
        # 列出相近名稱
        all_names = [Path(p).stem for p in state.get("processed_audio", [])]
        all_names += list(state.get("processed_folders", {}).keys())
        suggestions = [n for n in all_names if name.lower() in n.lower()]
        if suggestions:
            text = f"⚠️ 找不到 *{name}*\n\n你是不是指:\n" + "\n".join(f"  • {s}" for s in suggestions[:5])
        else:
            text = f"⚠️ 找不到 *{name}*\n\n用 /list 查看已處理的檔案"
        send_message(chat_id, text)


# ===== 音訊檔處理 =====

def handle_audio(chat_id, message: dict):
    """處理使用者傳來的音訊檔"""
    # Telegram 音訊可能在 audio, voice, document, video_note 欄位
    file_id = None
    file_name = None

    if "audio" in message:
        file_id = message["audio"]["file_id"]
        file_name = message["audio"].get("file_name", "audio.mp3")
    elif "voice" in message:
        file_id = message["voice"]["file_id"]
        file_name = "voice_note.ogg"
    elif "video_note" in message:
        file_id = message["video_note"]["file_id"]
        file_name = "video_note.mp4"
    elif "document" in message:
        doc = message["document"]
        mime = doc.get("mime_type", "")
        fname = doc.get("file_name", "")
        ext = Path(fname).suffix.lstrip(".").lower() if fname else ""
        if ext in AUDIO_EXTENSIONS or mime.startswith("audio/") or mime.startswith("video/"):
            file_id = doc["file_id"]
            file_name = fname or f"document.{ext or 'mp3'}"

    if not file_id:
        return False

    send_message(chat_id, f"📥 收到音訊: *{file_name}*\n⏳ 下載中...")

    # 下載到 ~/audio/
    dest = AUDIO_DIR / file_name
    if dest.exists():
        # 加時間戳避免覆蓋
        stem = dest.stem
        suffix = dest.suffix
        ts = datetime.now().strftime("%H%M%S")
        dest = AUDIO_DIR / f"{stem}_{ts}{suffix}"

    if not download_file(file_id, dest):
        send_message(chat_id, "❌ 下載失敗，請重試")
        return True

    send_message(
        chat_id,
        f"✅ 已儲存到 ~/audio/{dest.name}\n"
        f"🔄 Folder daemon 將自動處理，完成後會通知你\n\n"
        f"💡 如需合併投影片，建立 ~/audio/{dest.stem}/ 放入投影片即可"
    )
    return True


def handle_photo(chat_id, message: dict):
    """處理使用者傳來的圖片（投影片）"""
    send_message(
        chat_id,
        "🖼️ 收到圖片\n\n"
        "投影片圖片請直接放入 ~/audio/ 下的子資料夾中：\n"
        "  ~/audio/講題名稱/slide\\_01.jpg\n\n"
        "或用 /help 查看完整使用說明"
    )
    return True


# ===== 主處理 =====

def handle_update(update: dict):
    """處理一條 Telegram update"""
    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    # 只處理來自指定 chat 的訊息（安全性）
    if str(chat_id) != str(TG_CHAT_ID):
        log(f"⚠️ 忽略來自 chat_id={chat_id} 的訊息")
        return

    # 指令處理
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # 去掉 @botname
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/help" or cmd == "/start":
            cmd_help(chat_id)
        elif cmd == "/status":
            cmd_status(chat_id)
        elif cmd == "/list":
            cmd_list(chat_id)
        elif cmd == "/pending":
            cmd_pending(chat_id)
        elif cmd == "/rerun":
            cmd_rerun(chat_id, args)
        else:
            send_message(chat_id, f"❓ 不認識的指令: {cmd}\n用 /help 查看可用指令")
        return

    # 音訊檔處理
    if handle_audio(chat_id, msg):
        return

    # 圖片處理
    if "photo" in msg:
        handle_photo(chat_id, msg)
        return

    # 一般文字 → 提示
    if text:
        send_message(
            chat_id,
            f"💬 收到訊息: _{text}_\n\n"
            "用 /help 查看可用指令，或直接傳送音訊檔進行轉錄"
        )


def poll_updates():
    """Long polling 取得新訊息"""
    offset = load_offset()

    while True:
        try:
            params = {
                "offset": offset,
                "timeout": 30,
                "allowed_updates": json.dumps(["message"]),
            }
            result = tg_api("getUpdates", params, timeout=40)

            if result.get("ok") and result.get("result"):
                for update in result["result"]:
                    update_id = update["update_id"]
                    try:
                        handle_update(update)
                    except Exception as e:
                        log(f"❌ 處理 update {update_id} 失敗: {e}")
                        import traceback
                        traceback.print_exc()

                    offset = update_id + 1
                    save_offset(offset)

        except KeyboardInterrupt:
            log("👋 Bot 停止")
            break
        except Exception as e:
            log(f"⚠️ Poll 錯誤: {e}")
            time.sleep(5)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Telegram Bot 音訊處理")
    parser.add_argument("--daemon", action="store_true", help="背景模式")
    args = parser.parse_args()

    # 這隻程式沒有 token 就完全不能運作，早點講清楚比之後每個請求都失敗好
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("錯誤：請設定環境變數 TG_BOT_TOKEN 與 TG_CHAT_ID")
        print("      （token 請勿寫死在程式碼裡，這個 repo 是公開的）")
        sys.exit(1)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    log("🤖 Telegram Bot 啟動")
    log(f"  📂 音訊目錄: {AUDIO_DIR}")
    log(f"  🔑 Bot Token: ...{TG_BOT_TOKEN[-8:]}")
    log(f"  💬 Chat ID: {TG_CHAT_ID}")

    # 啟動通知
    send_message(TG_CHAT_ID, "🤖 Bot 已上線！傳 /help 查看指令")

    poll_updates()


if __name__ == "__main__":
    main()
