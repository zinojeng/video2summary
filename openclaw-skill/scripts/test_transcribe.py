#!/usr/bin/env python3
"""測試轉錄功能 - 診斷錯誤"""
import subprocess, os, sys
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "workspace" / "skills" / "audio-transcribe" / "scripts"
PYTHON = SKILL_DIR / "venv" / "bin" / "python3"
TRANSCRIBER = SKILL_DIR / "gpt4o_transcribe_clawbot.py"

# 載入 .env
env = os.environ.copy()
env_file = SKILL_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"')
            env["OPENAI_API_KEY"] = key
            print(f"API key: {key[:10]}...")

# 找測試檔案
audio = Path.home() / "inbox" / "gmail" / "ADA 2026 update 林思涵醫師.m4a"
if not audio.exists():
    # 找任何 m4a 檔案
    for f in (Path.home() / "inbox" / "gmail").glob("*.m4a"):
        audio = f
        break

print(f"Audio file: {audio}")
print(f"Exists: {audio.exists()}, Size: {audio.stat().st_size if audio.exists() else 0}")
print(f"Transcriber: {TRANSCRIBER}")
print(f"Transcriber exists: {TRANSCRIBER.exists()}")
print(f"Python: {PYTHON}")
print()

result = subprocess.run(
    [str(PYTHON), str(TRANSCRIBER),
     str(audio),
     "--language", "zh",
     "--format", "text",
     "--output", "/tmp/test_transcribe.txt"],
    capture_output=True, text=True, timeout=600,
    env=env, cwd=str(SKILL_DIR)
)

print(f"Return code: {result.returncode}")
print(f"STDOUT:\n{result.stdout[:1000] if result.stdout else '(empty)'}")
print(f"STDERR:\n{result.stderr[:1000] if result.stderr else '(empty)'}")
