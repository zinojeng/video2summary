#!/usr/bin/env python3
"""
測試改進的 GPT-4o 轉錄功能

使用方法：
    python test_improved_transcription.py <音頻檔案>
"""

import os
import sys

# 添加 speech2text 路徑
sys.path.insert(0, '/Users/zino/Desktop/OpenAI/speech2text/audio2text')

try:
    from gpt4o_stt_improved import transcribe_audio_gpt4o
    print("✓ 使用改進的 GPT-4o 轉錄模組")
except ImportError:
    from gpt4o_stt import transcribe_audio_gpt4o
    print("⚠ 使用原始的 GPT-4o 轉錄模組")


def test_transcription(audio_file):
    """測試轉錄功能"""
    
    # 檢查 API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("錯誤：請設定環境變數 OPENAI_API_KEY")
        return
        
    print(f"\n測試檔案: {audio_file}")
    print("-" * 60)
    
    try:
        # 測試基本轉錄
        print("\n1. 測試基本轉錄...")
        result = transcribe_audio_gpt4o(
            file_path=audio_file,
            api_key=api_key,
            model="gpt-4o-transcribe",
            language="zh",
            output_format="text",
            auto_convert=True  # 自動轉換格式
        )
        
        print("✓ 轉錄成功！")
        print(f"結果預覽: {result[:200]}...")
        
        # 測試 Markdown 格式
        print("\n2. 測試 Markdown 格式輸出...")
        result_md = transcribe_audio_gpt4o(
            file_path=audio_file,
            api_key=api_key,
            model="gpt-4o-transcribe",
            language="zh",
            output_format="markdown",
            auto_convert=True
        )
        
        print("✓ Markdown 格式成功！")
        
        # 儲存結果
        output_file = audio_file.rsplit(".", 1)[0] + "_transcription.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\n✓ 轉錄結果已儲存到: {output_file}")
        
    except Exception as e:
        print(f"\n✗ 轉錄失敗: {e}")
        
        # 嘗試使用 whisper-1 作為備用
        print("\n嘗試使用 whisper-1 模型...")
        try:
            result = transcribe_audio_gpt4o(
                file_path=audio_file,
                api_key=api_key,
                model="whisper-1",
                language="zh",
                output_format="text",
                auto_convert=True
            )
            print("✓ whisper-1 轉錄成功！")
            print(f"結果預覽: {result[:200]}...")
        except Exception as e2:
            print(f"✗ whisper-1 也失敗了: {e2}")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python test_improved_transcription.py <音頻檔案>")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"錯誤：找不到檔案 {audio_file}")
        sys.exit(1)
        
    test_transcription(audio_file)


if __name__ == "__main__":
    main()