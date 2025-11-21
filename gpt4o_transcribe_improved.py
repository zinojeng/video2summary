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
import shutil
from pathlib import Path
from openai import OpenAI
import mimetypes
import math


class AudioTranscriber:
    """音頻轉錄處理器"""
    
    SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
    VIDEO_FORMATS = {'.mp4', '.mov', '.mkv', '.avi', '.webm'}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
    
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def log_stage(self, message: str):
        """輸出階段提示"""
        print(f"[階段] {message}", flush=True)
        
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
            output_dir = tempfile.mkdtemp()
            
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            Path(input_path).stem + "_converted.mp3"
        )
        
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

    def extract_audio_from_video(self, video_path, output_dir=None):
        """從影片檔案提取音訊"""
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_path = os.path.join(
            output_dir,
            Path(video_path).stem + "_audio.mp3"
        )

        self.log_stage("偵測到影片檔案，提取音訊軌")

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "libmp3lame",
            "-b:a", "96k",
            "-y",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"音訊提取失敗：{result.stderr}")

        self.log_stage("音訊提取完成")
        return output_path

    def get_audio_duration(self, file_path):
        """取得音訊長度（秒）"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            try:
                return float(result.stdout.strip())
            except ValueError:
                return None
        return None
        
    def split_audio(self, input_path, segment_duration=600):
        """將音頻分割成小段（預設每段10分鐘）"""
        output_dir = Path(tempfile.mkdtemp())
        segments = []

        duration = self.get_audio_duration(input_path)
        if duration:
            num_segments = math.ceil(duration / segment_duration)
            print(f"音頻總時長：{duration:.1f} 秒，將分割為 {num_segments} 段")

        ext = Path(input_path).suffix or ".mp3"
        output_pattern = output_dir / f"segment_%03d{ext}"

        cmd = [
            "ffmpeg", "-i", input_path,
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-c", "copy",
            "-reset_timestamps", "1",
            "-avoid_negative_ts", "1",
            "-y",
            str(output_pattern)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"音頻切割失敗：{result.stderr}")

        for segment_file in sorted(output_dir.glob(f"segment_*{ext}")):
            segment_duration_value = segment_duration
            if duration:
                start_index = len(segments)
                start_time = start_index * segment_duration
                remaining = max(duration - start_time, 0)
                segment_duration_value = min(segment_duration, remaining)
            else:
                start_time = len(segments) * segment_duration

            segments.append({
                'path': str(segment_file),
                'start': start_time,
                'duration': segment_duration_value
            })

        return segments, str(output_dir)
        
    def transcribe_file(
        self,
        file_path,
        model="gpt-4o-transcribe",
        language="zh",
        response_format="text",
        request_timeout=90,
    ):
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
            response_format=actual_format,
            timeout=request_timeout,
        )
            
        return transcript
        
    def transcribe(
        self,
        audio_path,
        model="gpt-4o-transcribe",
        language="zh",
        output_format="text",
        auto_convert=True,
        segment_duration=600,
        request_timeout=90,
    ):
        """主要轉錄功能，處理所有邏輯"""
        self.log_stage("檢查音頻格式與大小")

        process_path = audio_path
        temp_files = []
        temp_dirs = []

        try:
            ext = Path(process_path).suffix.lower()
            if ext in self.VIDEO_FORMATS:
                video_dir = tempfile.mkdtemp()
                temp_dirs.append(video_dir)
                process_path = self.extract_audio_from_video(process_path, video_dir)
                temp_files.append(process_path)
                ext = Path(process_path).suffix.lower()

            audio_info = self.check_audio_format(process_path)

            print("\n音頻檔案資訊：")
            print(f"  原始路徑: {audio_path}")
            print(f"  處理路徑: {process_path}")
            print(f"  大小: {audio_info['size']:,} bytes ({audio_info['size']/1024/1024:.2f} MB)")
            print(f"  格式: {audio_info['extension']}")
            print(f"  支援: {'是' if audio_info['supported'] else '否'}")
            print(f"  超過大小限制: {'是' if audio_info['too_large'] else '否'}")

            if not audio_info['supported'] or (auto_convert and audio_info['extension'] != '.mp3'):
                print("\n需要轉換音頻格式...")
                self.log_stage("轉換為高相容性 MP3 格式")
                convert_dir = tempfile.mkdtemp()
                temp_dirs.append(convert_dir)
                process_path = self.convert_to_compatible_format(process_path, convert_dir)
                temp_files.append(process_path)
                audio_info = self.check_audio_format(process_path)

            duration = self.get_audio_duration(process_path)
            if duration:
                print(f"  音訊長度: {duration:.1f} 秒 ({duration/60:.1f} 分鐘)")

            needs_split = audio_info['too_large']
            if duration and segment_duration:
                needs_split = needs_split or duration > segment_duration

            if needs_split:
                print(f"\n檔案需要分段處理（每段 {segment_duration/60:.1f} 分鐘）...")
                self.log_stage("音檔過大，開始分段轉錄")
                segments, segment_dir = self.split_audio(process_path, segment_duration=segment_duration)
                temp_dirs.append(segment_dir)

                all_transcripts = []
                for i, segment in enumerate(segments):
                    print(f"\n處理第 {i+1}/{len(segments)} 段...")
                    self.log_stage(f"上傳第 {i+1}/{len(segments)} 段並等待回應")
                    try:
                        transcript = self.transcribe_file(
                            segment['path'],
                            model,
                            language,
                            "text",
                            request_timeout=request_timeout,
                        )
                        transcript_text = transcript if isinstance(transcript, str) else transcript.text
                        all_transcripts.append({
                            'text': transcript_text,
                            'start': segment['start'],
                            'duration': segment['duration']
                        })
                        print(f"✓ 第 {i+1} 段轉錄成功")
                        self.log_stage(f"第 {i+1}/{len(segments)} 段回應已取得")
                    except Exception as e:
                        print(f"✗ 第 {i+1} 段轉錄失敗: {e}")

                if output_format == "srt":
                    final_text = self.generate_srt_from_segments(all_transcripts)
                else:
                    final_text = "\n\n".join([seg['text'] for seg in all_transcripts])

            else:
                print("\n開始轉錄...")
                self.log_stage("上傳音檔並等待模型回應")
                transcript = self.transcribe_file(
                    process_path,
                    model,
                    language,
                    output_format,
                    request_timeout=request_timeout,
                )
                final_text = transcript if isinstance(transcript, str) else transcript.text
                self.log_stage("模型回應已取得")

            if output_format == "markdown":
                final_text = f"# 語音轉錄結果\n\n{final_text}\n"
            elif output_format == "srt" and isinstance(final_text, str) and not final_text.startswith("1\n"):
                final_text = self.generate_srt_fallback(final_text)

            self.log_stage("整理輸出內容")

            if not needs_split:
                print(f"\n轉錄完成！總字數：{len(final_text)} 字元")
            else:
                total_duration = sum(seg['duration'] for seg in all_transcripts if isinstance(seg, dict))
                total_chars = len(final_text)
                print("\n轉錄完成！")
                print(f"  處理時長：{total_duration:.1f} 秒 ({total_duration/60:.1f} 分鐘)")
                print(f"  總字數：{total_chars:,} 字元")
                if total_duration:
                    print(f"  平均速度：{total_chars/total_duration*60:.0f} 字元/分鐘")

            return final_text

        except Exception as e:
            raise Exception(f"轉錄失敗: {str(e)}")

        finally:
            for tmp_file in temp_files:
                if tmp_file and os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except OSError:
                        pass
            for tmp_dir in temp_dirs:
                if tmp_dir and os.path.isdir(tmp_dir):
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                
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
                       choices=["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"],
                       help="選擇模型")
    parser.add_argument("--language", default="zh", help="語言代碼")
    parser.add_argument("--format", default="text",
                       choices=["text", "markdown", "srt"],
                       help="輸出格式 (text=純文字, markdown=MD格式, srt=字幕格式)")
    parser.add_argument("--no-convert", action="store_true",
                       help="不自動轉換音頻格式")
    parser.add_argument("--output", help="輸出檔案路徑（預設輸出到終端）")
    parser.add_argument("--max-segment-seconds", type=int, default=600,
                       help="分段長度（秒），預設 600 秒 (10 分鐘)")
    parser.add_argument("--request-timeout", type=int, default=90,
                       help="OpenAI API 請求逾時秒數 (預設 90 秒)")
    
    args = parser.parse_args()

    if args.max_segment_seconds <= 0:
        print("錯誤：max-segment-seconds 需為正整數")
        sys.exit(1)
    
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
            auto_convert=not args.no_convert,
            segment_duration=args.max_segment_seconds,
            request_timeout=args.request_timeout,
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
