#!/usr/bin/env python3
"""
測試修正後的轉錄功能
"""

import os
import sys
from openai import OpenAI
import io

def test_transcribe_with_bytesio(audio_file_path, api_key):
    """測試使用 BytesIO 的轉錄方法"""
    
    if not os.path.exists(audio_file_path):
        print(f"錯誤：找不到檔案 {audio_file_path}")
        return
        
    print(f"測試檔案: {audio_file_path}")
    print(f"檔案大小: {os.path.getsize(audio_file_path):,} bytes")
    
    # 獲取檔案名稱
    file_name = os.path.basename(audio_file_path)
    if not file_name.endswith(('.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm')):
        file_name = file_name.split('.')[0] + '.mp3'
        
    print(f"使用檔名: {file_name}")
    
    # 讀取檔案內容
    with open(audio_file_path, "rb") as f:
        file_content = f.read()
        
    # 創建 BytesIO 物件
    file_like = io.BytesIO(file_content)
    file_like.name = file_name  # 這樣就可以設定 name 屬性
    
    # 測試轉錄
    client = OpenAI(api_key=api_key)
    
    try:
        print("\n開始轉錄...")
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=file_like,
            language="zh",
            response_format="text"
        )
        
        print("✓ 轉錄成功！")
        print(f"結果預覽: {transcript.text[:200]}...")
        
    except Exception as e:
        print(f"✗ 轉錄失敗: {e}")
        
        # 嘗試 whisper-1
        print("\n嘗試 whisper-1 模型...")
        try:
            # 重新創建 BytesIO（因為之前的已經被讀取）
            file_like = io.BytesIO(file_content)
            file_like.name = file_name
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=file_like,
                language="zh",
                response_format="text"
            )
            print("✓ whisper-1 轉錄成功！")
            print(f"結果預覽: {transcript.text[:200]}...")
        except Exception as e2:
            print(f"✗ whisper-1 也失敗了: {e2}")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python test_fix_transcription.py <音頻檔案>")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("請設定環境變數 OPENAI_API_KEY")
        sys.exit(1)
        
    test_transcribe_with_bytesio(audio_file, api_key)


if __name__ == "__main__":
    main()