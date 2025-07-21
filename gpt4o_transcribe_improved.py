"""
gpt4o_transcribe_improved.py

改進的 GPT-4o 語音轉文字程式，處理常見的音頻格式和檔案問題

特點：
1. 自動檢測音頻格式並轉換為高相容性格式
2. 處理大檔案（>25MB）自動分段
3. 正確設定檔名和 MIME 類型
4. 完整的錯誤處理和診斷資訊
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI
import mimetypes
import math


class AudioTranscriber:
    """音頻轉錄處理器"""
    
    SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
    
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        
    def check_audio_format(self, file_path):
        """檢查音頻格式並返回資訊"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到檔案：{file_path}")
            
        file_size = os.path.getsize(file_path)
        file_ext = Path(file_path).suffix.lower()
        
        # 使用 ffprobe 獲取詳細資訊
        try:
            cmd = [
                "ffprobe", "-v", "error", 
                "-show_entries", "format=format_name,duration,bit_rate,size:stream=codec_name,sample_rate,channels",
                "-of", "json", file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                return {
                    'path': file_path,
                    'size': file_size,
                    'extension': file_ext,
                    'format_info': info,
                    'supported': file_ext in self.SUPPORTED_FORMATS,
                    'too_large': file_size > self.MAX_FILE_SIZE
                }
        except:
            pass
            
        return {
            'path': file_path,
            'size': file_size,
            'extension': file_ext,
            'supported': file_ext in self.SUPPORTED_FORMATS,
            'too_large': file_size > self.MAX_FILE_SIZE
        }
        
    def convert_to_compatible_format(self, input_path, output_dir=None):
        """轉換為高相容性的 MP3 格式"""
        if output_dir is None:
            output_dir = tempfile.gettempdir()
            
        output_path = os.path.join(output_dir, 
                                  Path(input_path).stem + "_converted.mp3")
        
        print(f"正在轉換音頻格式...")
        print(f"  輸入: {input_path}")
        print(f"  輸出: {output_path}")
        
        # 使用推薦的參數轉換
        cmd = [
            "ffmpeg", "-i", input_path,
            "-ar", "16000",      # 16kHz 採樣率
            "-ac", "1",          # 單聲道
            "-c:a", "libmp3lame", # MP3 編碼器
            "-b:a", "64k",       # 固定位元率 64kbps
            "-y",                # 覆蓋輸出檔案
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"音頻轉換失敗：{result.stderr}")
            
        print(f"✓ 轉換成功！檔案大小：{os.path.getsize(output_path):,} bytes")
        return output_path
        
    def split_audio(self, input_path, segment_duration=600):
        """將音頻分割成小段（預設每段10分鐘）"""
        output_dir = tempfile.mkdtemp()
        segments = []
        
        # 獲取音頻總時長
        cmd = ["ffprobe", "-v", "error", "-show_entries", 
               "format=duration", "-of", "json", input_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            duration = float(json.loads(result.stdout)['format']['duration'])
            num_segments = math.ceil(duration / segment_duration)
            
            print(f"音頻總時長：{duration:.1f} 秒，將分割為 {num_segments} 段")
            
            for i in range(num_segments):
                start_time = i * segment_duration
                output_path = os.path.join(output_dir, f"segment_{i:03d}.mp3")
                
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-ss", str(start_time),
                    "-t", str(segment_duration),
                    "-ar", "16000",
                    "-ac", "1",
                    "-c:a", "libmp3lame",
                    "-b:a", "64k",
                    "-y",
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True)
                if os.path.exists(output_path):
                    segments.append({
                        'path': output_path,
                        'start': start_time,
                        'duration': min(segment_duration, duration - start_time)
                    })
                    
        return segments
        
    def transcribe_file(self, file_path, model="gpt-4o-transcribe", 
                       language="zh", response_format="text"):
        """轉錄單個音頻檔案"""
        # 確保檔案有正確的副檔名
        file_name = os.path.basename(file_path)
        if not Path(file_name).suffix:
            file_name = file_name + ".mp3"
            
        # 使用元組格式來傳遞檔案，這樣可以指定檔名
        with open(file_path, "rb") as f:
            # 讀取檔案內容
            file_content = f.read()
            
        # 創建類似檔案的物件並設定名稱
        import io
        file_like = io.BytesIO(file_content)
        file_like.name = file_name  # BytesIO 允許設定 name 屬性
        
        # GPT-4o models only support 'text' and 'json' formats
        # For SRT, we'll get text and convert it later
        actual_format = "text"
        
        transcript = self.client.audio.transcriptions.create(
            model=model,
            file=file_like,
            language=language,
            response_format=actual_format
        )
            
        return transcript
        
    def transcribe(self, audio_path, model="gpt-4o-transcribe", 
                  language="zh", output_format="text", auto_convert=True):
        """主要轉錄功能，處理所有邏輯"""
        # 檢查音頻格式
        audio_info = self.check_audio_format(audio_path)
        
        print(f"\n音頻檔案資訊：")
        print(f"  路徑: {audio_info['path']}")
        print(f"  大小: {audio_info['size']:,} bytes ({audio_info['size']/1024/1024:.2f} MB)")
        print(f"  格式: {audio_info['extension']}")
        print(f"  支援: {'是' if audio_info['supported'] else '否'}")
        print(f"  超過大小限制: {'是' if audio_info['too_large'] else '否'}")
        
        # 決定處理方式
        process_path = audio_path
        temp_file = None
        
        try:
            # 如果格式不支援或需要轉換
            if not audio_info['supported'] or (auto_convert and audio_info['extension'] != '.mp3'):
                print(f"\n需要轉換音頻格式...")
                process_path = self.convert_to_compatible_format(audio_path)
                temp_file = process_path
                audio_info = self.check_audio_format(process_path)
                
            # 如果檔案太大，需要分段
            if audio_info['too_large']:
                print(f"\n檔案超過 25MB，需要分段處理...")
                segments = self.split_audio(process_path)
                
                all_transcripts = []
                for i, segment in enumerate(segments):
                    print(f"\n處理第 {i+1}/{len(segments)} 段...")
                    try:
                        # 對於分段轉錄，始終使用 text 格式
                        transcript = self.transcribe_file(
                            segment['path'], model, language, "text"
                        )
                        # GPT-4o models return string directly
                        transcript_text = transcript if isinstance(transcript, str) else transcript.text
                        all_transcripts.append({
                            'text': transcript_text,
                            'start': segment['start'],
                            'duration': segment['duration']
                        })
                        print(f"✓ 第 {i+1} 段轉錄成功")
                    except Exception as e:
                        print(f"✗ 第 {i+1} 段轉錄失敗: {e}")
                    finally:
                        # 清理分段檔案
                        if os.path.exists(segment['path']):
                            os.remove(segment['path'])
                            
                # 根據輸出格式合併結果
                if output_format == "srt":
                    # 生成 SRT 格式
                    final_text = self.generate_srt_from_segments(all_transcripts)
                else:
                    # 合併純文字，每段之間加入雙換行
                    final_text = "\n\n".join([seg['text'] for seg in all_transcripts])
                
            else:
                # 直接轉錄
                print(f"\n開始轉錄...")
                transcript = self.transcribe_file(
                    process_path, model, language, output_format
                )
                final_text = transcript if isinstance(transcript, str) else transcript.text
                
            # 格式化輸出
            if output_format == "markdown":
                final_text = f"# 語音轉錄結果\n\n{final_text}\n"
            elif output_format == "srt" and isinstance(final_text, str) and not final_text.startswith("1\n"):
                # 如果 API 沒有返回 SRT 格式，使用回退方法生成
                final_text = self.generate_srt_fallback(final_text)
                
            # 顯示轉錄摘要
            if not audio_info['too_large']:
                print(f"\n轉錄完成！總字數：{len(final_text)} 字元")
            else:
                # 對於分段轉錄，顯示更詳細的資訊
                total_duration = sum(seg['duration'] for seg in all_transcripts if isinstance(seg, dict))
                total_chars = len(final_text)
                print(f"\n轉錄完成！")
                print(f"  處理時長：{total_duration:.1f} 秒 ({total_duration/60:.1f} 分鐘)")
                print(f"  總字數：{total_chars:,} 字元")
                print(f"  平均速度：{total_chars/total_duration*60:.0f} 字元/分鐘")
                
            return final_text
            
        except Exception as e:
            raise Exception(f"轉錄失敗: {str(e)}")
            
        finally:
            # 清理臨時檔案
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
                
    def generate_srt_from_segments(self, segments):
        """從分段結果生成 SRT 格式"""
        srt_content = []
        subtitle_index = 1
        
        for segment in segments:
            text = segment['text']
            start_time = segment['start']
            duration = segment['duration']
            
            # 將文字分成句子
            sentences = [s.strip() for s in text.replace('。', '.').split('.') if s.strip()]
            
            if not sentences:
                continue
                
            # 計算每個句子的時長
            sentence_duration = duration / len(sentences)
            
            for j, sentence in enumerate(sentences):
                subtitle_start = start_time + (j * sentence_duration)
                subtitle_end = subtitle_start + sentence_duration
                
                start_srt = self.format_srt_time(subtitle_start)
                end_srt = self.format_srt_time(subtitle_end)
                
                srt_content.append(f"{subtitle_index}")
                srt_content.append(f"{start_srt} --> {end_srt}")
                srt_content.append(sentence + '。')
                srt_content.append("")  # 空行分隔
                subtitle_index += 1
                
        return "\n".join(srt_content)
        
    def generate_srt_fallback(self, text):
        """當 API 不支援 SRT 格式時的回退方法"""
        sentences = [s.strip() for s in text.replace('。', '.').split('.') if s.strip()]
        srt_content = []
        subtitle_index = 1
        time_offset = 0
        
        # 假設平均每個字 0.3 秒
        for sentence in sentences:
            duration = len(sentence) * 0.3
            duration = max(duration, 2.0)  # 最少 2 秒
            duration = min(duration, 10.0)  # 最多 10 秒
            
            start_time = time_offset
            end_time = time_offset + duration
            
            start_srt = self.format_srt_time(start_time)
            end_srt = self.format_srt_time(end_time)
            
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{start_srt} --> {end_srt}")
            srt_content.append(sentence + '。')
            srt_content.append("")  # 空行分隔
            
            subtitle_index += 1
            time_offset = end_time
            
        return "\n".join(srt_content)
        
    def format_srt_time(self, seconds):
        """將秒數轉換為 SRT 時間格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def main():
    parser = argparse.ArgumentParser(
        description="改進的 GPT-4o 語音轉文字工具"
    )
    parser.add_argument("audio_file", help="音頻檔案路徑")
    parser.add_argument("--model", default="gpt-4o-transcribe",
                       choices=["gpt-4o-transcribe", "gpt-4o-mini-transcribe"],
                       help="選擇模型")
    parser.add_argument("--language", default="zh", help="語言代碼")
    parser.add_argument("--format", default="text",
                       choices=["text", "markdown", "srt"],
                       help="輸出格式 (text=純文字, markdown=MD格式, srt=字幕格式)")
    parser.add_argument("--no-convert", action="store_true",
                       help="不自動轉換音頻格式")
    parser.add_argument("--output", help="輸出檔案路徑（預設輸出到終端）")
    
    args = parser.parse_args()
    
    # 檢查 API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("錯誤：請設定環境變數 OPENAI_API_KEY")
        sys.exit(1)
        
    # 檢查 ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except:
        print("警告：未找到 ffmpeg，某些功能可能無法使用")
        print("請安裝 ffmpeg: brew install ffmpeg")
        
    # 執行轉錄
    try:
        transcriber = AudioTranscriber(api_key)
        result = transcriber.transcribe(
            args.audio_file,
            model=args.model,
            language=args.language,
            output_format=args.format,
            auto_convert=not args.no_convert
        )
        
        # 輸出結果
        if args.output:
            # 如果沒有指定副檔名，根據格式自動添加
            output_path = args.output
            if not Path(output_path).suffix:
                ext_map = {
                    "text": ".txt",
                    "markdown": ".md",
                    "srt": ".srt"
                }
                output_path = output_path + ext_map.get(args.format, ".txt")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"\n✓ 轉錄結果已儲存到：{output_path}")
        else:
            print("\n" + "="*60)
            print("轉錄結果：")
            print("="*60)
            print(result)
            
    except Exception as e:
        print(f"\n錯誤：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()