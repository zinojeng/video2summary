"""
debug_transcription.py

診斷音頻轉錄問題的工具
"""

import os
import sys
from pathlib import Path
from openai import OpenAI
import mimetypes
import subprocess


def check_audio_file(file_path):
    """檢查音頻檔案的詳細資訊"""
    
    print("=" * 60)
    print(f"檢查檔案: {file_path}")
    print("=" * 60)
    
    # 基本檢查
    if not os.path.exists(file_path):
        print("❌ 錯誤：檔案不存在")
        return False
        
    file_size = os.path.getsize(file_path)
    print(f"✓ 檔案大小: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    if file_size == 0:
        print("❌ 錯誤：檔案是空的")
        return False
        
    # 檢查 MIME 類型
    mime_type, _ = mimetypes.guess_type(file_path)
    print(f"✓ MIME 類型: {mime_type}")
    
    # 讀取檔案頭
    with open(file_path, "rb") as f:
        header = f.read(32)
        print(f"✓ 檔案頭 (前32 bytes): {header[:16].hex()}")
        
        # 檢查常見音頻格式標識
        if header.startswith(b"RIFF") and b"WAVE" in header:
            print("  → 檢測到 WAV 格式")
        elif header.startswith(b"\xff\xfb") or header.startswith(b"ID3"):
            print("  → 檢測到 MP3 格式")
        elif header.startswith(b"fLaC"):
            print("  → 檢測到 FLAC 格式")
        elif b"ftyp" in header[:12]:
            print("  → 檢測到 MP4/M4A 格式")
        elif header.startswith(b"OggS"):
            print("  → 檢測到 OGG 格式")
        else:
            print("  → 未識別的格式")
            
    # 如果有 ffprobe，使用它來獲取更多資訊
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", file_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("\n✓ FFprobe 分析:")
            import json
            info = json.loads(result.stdout)
            if "format" in info:
                fmt = info["format"]
                print(f"  格式: {fmt.get('format_name', 'unknown')}")
                print(f"  時長: {float(fmt.get('duration', 0)):.2f} 秒")
                print(f"  位元率: {int(fmt.get('bit_rate', 0)):,} bps")
    except:
        print("\n(ffprobe 不可用，跳過詳細分析)")
        
    return True


def test_openai_transcription(file_path, api_key):
    """測試 OpenAI 轉錄"""
    
    print("\n" + "=" * 60)
    print("測試 OpenAI 轉錄")
    print("=" * 60)
    
    client = OpenAI(api_key=api_key)
    
    # 測試不同的模型
    models = [
        ("gpt-4o-transcribe", "GPT-4o 轉錄模型"),
        ("whisper-1", "Whisper 模型")
    ]
    
    for model_name, model_desc in models:
        print(f"\n嘗試 {model_desc} ({model_name})...")
        
        try:
            with open(file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model=model_name,
                    file=audio_file,
                    language="zh",
                    response_format="text"
                )
                
            print(f"✓ {model_desc} 轉錄成功！")
            print(f"結果預覽: {transcript.text[:200]}...")
            return True
            
        except Exception as e:
            print(f"❌ {model_desc} 失敗: {e}")
            
    return False


def convert_audio_format(input_path, output_format="mp3"):
    """嘗試轉換音頻格式"""
    
    print("\n" + "=" * 60)
    print(f"嘗試轉換為 {output_format.upper()} 格式")
    print("=" * 60)
    
    output_path = input_path.rsplit(".", 1)[0] + f"_converted.{output_format}"
    
    try:
        # 使用 ffmpeg 轉換
        cmd = [
            "ffmpeg", "-i", input_path,
            "-acodec", "libmp3lame" if output_format == "mp3" else "pcm_s16le",
            "-ar", "16000",  # 16kHz 採樣率
            "-ac", "1",      # 單聲道
            "-y",            # 覆蓋輸出檔案
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ 成功轉換為 {output_path}")
            return output_path
        else:
            print(f"❌ 轉換失敗: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 轉換錯誤: {e}")
        
    return None


def main():
    if len(sys.argv) < 2:
        print("使用方法: python debug_transcription.py <音頻檔案路徑>")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("請設定環境變數 OPENAI_API_KEY")
        sys.exit(1)
        
    # 步驟 1: 檢查原始檔案
    if not check_audio_file(audio_file):
        return
        
    # 步驟 2: 測試轉錄
    success = test_openai_transcription(audio_file, api_key)
    
    # 步驟 3: 如果失敗，嘗試轉換格式
    if not success:
        print("\n原始檔案轉錄失敗，嘗試轉換格式...")
        
        # 嘗試轉換為 MP3
        converted_file = convert_audio_format(audio_file, "mp3")
        if converted_file and os.path.exists(converted_file):
            check_audio_file(converted_file)
            test_openai_transcription(converted_file, api_key)
            
            # 清理轉換的檔案
            # os.remove(converted_file)
            print(f"\n(轉換的檔案保留在: {converted_file})")


if __name__ == "__main__":
    main()