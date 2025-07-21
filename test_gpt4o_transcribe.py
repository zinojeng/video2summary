"""
test_gpt4o_transcribe.py

測試 GPT-4o 轉錄功能，處理音頻檔案錯誤問題
"""

import os
import sys
from openai import OpenAI


def test_transcribe(audio_file_path, api_key):
    """測試轉錄功能"""
    
    # 檢查檔案是否存在
    if not os.path.exists(audio_file_path):
        print(f"錯誤：找不到檔案 {audio_file_path}")
        return
        
    # 獲取檔案大小
    file_size = os.path.getsize(audio_file_path)
    print(f"檔案路徑: {audio_file_path}")
    print(f"檔案大小: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # 檢查檔案是否為空
    if file_size == 0:
        print("錯誤：檔案是空的")
        return
        
    # 讀取檔案前幾個 bytes 來檢查格式
    with open(audio_file_path, "rb") as f:
        header = f.read(16)
        print(f"檔案頭 (前16 bytes): {header.hex()}")
        
    client = OpenAI(api_key=api_key)
    
    try:
        print("\n開始轉錄...")
        
        with open(audio_file_path, "rb") as audio_file:
            # 嘗試基本轉錄
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                language="zh",
                response_format="text"
            )
            
        print("\n轉錄成功！")
        print(f"轉錄結果:\n{transcript.text}")
        
    except Exception as e:
        print(f"\n轉錄失敗: {e}")
        
        # 如果是檔案格式問題，嘗試不同的方法
        if "corrupted" in str(e) or "unsupported" in str(e):
            print("\n檔案可能已損壞或格式不支援")
            print("支援的格式: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm")
            
            # 嘗試使用 whisper-1 模型
            print("\n嘗試使用 whisper-1 模型...")
            try:
                with open(audio_file_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="zh",
                        response_format="text"
                    )
                print("whisper-1 轉錄成功！")
                print(f"轉錄結果:\n{transcript.text}")
            except Exception as e2:
                print(f"whisper-1 也失敗了: {e2}")


def main():
    # 從命令行參數獲取檔案路徑
    if len(sys.argv) < 2:
        print("使用方法: python test_gpt4o_transcribe.py <音頻檔案路徑>")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    
    # 獲取 API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("請設定環境變數 OPENAI_API_KEY")
        sys.exit(1)
        
    test_transcribe(audio_file, api_key)


if __name__ == "__main__":
    main()