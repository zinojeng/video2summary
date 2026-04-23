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
import math


class AudioTranscriber:
    """音頻轉錄處理器"""

    SUPPORTED_FORMATS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}
    # 高相容性格式：這些格式不需要轉換，OpenAI API 直接支援
    HIGH_COMPAT_FORMATS = {'.mp3', '.m4a', '.wav'}
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

    def detect_repetition(self, text: str, min_phrase_len: int = 15, max_repeat: int = 3) -> dict:
        """偵測轉錄文字中的重複迴圈 (Whisper repetition loop bug)

        Returns:
            dict with keys:
                'has_repetition': bool
                'clean_text': str (截斷重複後的乾淨文字)
                'repeat_ratio': float (重複佔全文比例)
                'repeated_phrase': str (被重複的片段)
        """
        if not text or len(text) < min_phrase_len * max_repeat:
            return {'has_repetition': False, 'clean_text': text, 'repeat_ratio': 0.0, 'repeated_phrase': ''}

        # 方法 1: 尋找連續重複的子字串
        best_match = {'phrase': '', 'count': 0, 'start': 0}

        # 嘗試不同長度的 phrase (從長到短)
        for phrase_len in range(min(80, len(text) // 3), min_phrase_len - 1, -1):
            for start in range(0, len(text) - phrase_len * 2):
                phrase = text[start:start + phrase_len]
                if not phrase.strip():
                    continue

                # 計算連續重複次數
                count = 1
                pos = start + phrase_len
                while pos + phrase_len <= len(text):
                    if text[pos:pos + phrase_len] == phrase:
                        count += 1
                        pos += phrase_len
                    else:
                        break

                if count >= max_repeat and count > best_match['count']:
                    best_match = {'phrase': phrase, 'count': count, 'start': start}

            # 找到足夠多重複就停止
            if best_match['count'] >= max_repeat:
                break

        if best_match['count'] >= max_repeat:
            repeat_len = best_match['count'] * len(best_match['phrase'])
            repeat_ratio = repeat_len / len(text)

            # 截斷：保留重複開始前的內容 + 一次重複片段
            clean_end = best_match['start'] + len(best_match['phrase'])
            clean_text = text[:clean_end].rstrip()

            return {
                'has_repetition': True,
                'clean_text': clean_text,
                'repeat_ratio': repeat_ratio,
                'repeated_phrase': best_match['phrase'][:100],
                'repeat_count': best_match['count'],
            }

        return {'has_repetition': False, 'clean_text': text, 'repeat_ratio': 0.0, 'repeated_phrase': ''}

    def split_audio(self, input_path, segment_duration=600):
        """將音頻分割成小段（預設每段10分鐘），並儲存到 persistent 資料夾"""
        
        # 建立 persistent output dir: {original_filename}_parts/segments
        input_path_obj = Path(input_path)
        base_dir = input_path_obj.parent / f"{input_path_obj.stem}_parts"
        segments_dir = base_dir / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        
        segments = []

        duration = self.get_audio_duration(input_path)
        if duration:
            num_segments = math.ceil(duration / segment_duration)
            print(f"音頻總時長：{duration:.1f} 秒，將分割為 {num_segments} 段")
            print(f"分段儲存目錄：{segments_dir}")

        ext = input_path_obj.suffix or ".mp3"
        # 使用一致的命名模式：segment_000.mp3
        output_pattern = segments_dir / f"segment_%03d{ext}"

        # 檢查是否已經分割過 (簡單檢查：如果 segment_000 存在)
        # 為了更嚴謹，我們可以重新執行 ffmpeg，它會因為我們用了 -y 而覆蓋，或者我們可以檢查是否已有檔案
        # 這裡為了確保一致性，我們還是跑一次 ffmpeg，但如果檔案已存在且大小合理，ffmpeg 可能會比較慢？
        # 實際上 ffmpeg 分割很快 (copy codec)，所以重跑還好，能確保正確性。
        
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

        for segment_file in sorted(segments_dir.glob(f"segment_*{ext}")):
            segment_duration_value = segment_duration
            # 計算該段的預估時長
            # 注意：這裡只是預估，用於顯示進度，準確時長由 ffmpeg 決定
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

        return segments, str(base_dir)

    def transcribe_file(
        self,
        file_path,
        model="gpt-4o-transcribe",
        language="zh",
        response_format="text",  # 保留參數以維持 API 相容性，但內部固定使用 json 格式
        request_timeout=90,
        prompt_context=None,
    ):
        """轉錄單個音頻檔案

        Note: response_format 參數保留以維持向後相容，但 OpenAI API 呼叫時
        固定使用 json 格式以取得時間戳資訊（gpt-4o-transcribe 模型只支援 json/text）。
        """
        _ = response_format  # 標記為有意忽略
        # 確保檔案有正確的副檔名
        file_name = os.path.basename(file_path)
        if not Path(file_name).suffix:
            file_name = file_name + ".mp3"
            
        print(f"[Model] Using model: {model}")

        # Gemini Model Handling
        if "gemini" in model.lower():
            import google.generativeai as genai
            gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not gemini_key:
                raise ValueError("Missing GEMINI_API_KEY or GOOGLE_API_KEY for Gemini models.")
            
            genai.configure(api_key=gemini_key)
            
            # Ensure model name starts with 'models/' for Google GenAI SDK
            api_model_name = model
            if not api_model_name.startswith("models/"):
                 api_model_name = f"models/{model}"

            print(f"[Gemini] Uploading file to Gemini...")
            audio_file = genai.upload_file(file_path, mime_type="audio/mp3")
            
            prompt = "Generate a transcript of the speech."
            if language:
                # Force Traditional Chinese if zh/zh-tw is requested
                if language.lower() in ['zh', 'zh-tw', 'zh-hk']:
                     prompt += f" The language is Traditional Chinese (Taiwan). Please output in Traditional Chinese (繁體中文)."
                else:
                     prompt += f" The language is {language}."
            
            if prompt_context:
                prompt += f"\n\nPrevious Context (for continuity, do not repeat): {prompt_context}"

            print(f"[Gemini] Generating content...")
            gemini_model = genai.GenerativeModel(api_model_name)
            
            # Retry logic for Gemini
            max_retries = 3
            import time
            
            for attempt in range(max_retries):
                try:
                    # Use explicit timeout if possible, though genai SDK uses request_options in recent versions
                    # We pass request_timeout to request_options if supported, otherwise it relies on default
                    response = gemini_model.generate_content(
                        [prompt, audio_file],
                        request_options={'timeout': request_timeout} 
                    )
                    return response.text
                except Exception as e:
                    print(f"⚠️  Gemini Error (Attempt {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        print(f"   Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        raise e

        # OpenAI Handling (Default)
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        import io
        file_like = io.BytesIO(file_content)
        file_like.name = file_name
        
        # Note: OpenAI 'transcriptions' endpoint does not support system prompt for style.
        # It blindly transcribes what it hears.
        # If the audio is Mandarin, it might output Simplified.
        # We rely on the `translate` feature explicitly properly converting it later.
        
        # Prepare arguments
        # gpt-4o-transcribe 模型只支援 'json' 或 'text' 格式
        # 使用 'json' 格式可取得時間戳資訊
        kwargs = {
            "model": model,
            "file": file_like,
            "language": language,
            "response_format": "json",
            "timeout": request_timeout,
        }
        
        if prompt_context:
            kwargs["prompt"] = prompt_context

        transcript = self.client.audio.transcriptions.create(**kwargs)
            
        return transcript

    def translate_text(self, text, target_lang, model="gpt-4o"):
        """翻譯文字"""
        if not text or not text.strip():
            return ""
            
        lang_name_map = {
            "zh-tw": "Traditional Chinese (Taiwan)",
            "en": "English",
            "zh": "Traditional Chinese",
            "ja": "Japanese"
        }
        target_lang_name = lang_name_map.get(target_lang.lower(), target_lang)
        
        system_prompt = f"You are a professional translator. Translate the following text into natural, fluent {target_lang_name}. Maintain the original meaning and tone."
        user_prompt = f"{text}"

        print(f"[Translation] Translating to {target_lang_name}...")

        # Gemini
        if "gemini" in model.lower():
            import google.generativeai as genai
            try:
                # Reuse Gemini configuration logic or check if configured
                gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if gemini_key:
                     genai.configure(api_key=gemini_key)
                
                # Use a specific text model for translation if needed, or the same model
                # For safety, use a known text model or the same one passed in (if text-capable)
                # Let's try to use the model passed in, but strip 'transcribe' if present or use a sturdy one
                # Actually, gemini-1.5-flash is good for this.
                trans_model_name = "models/gemini-1.5-flash"
                if "gemini" in model:
                     trans_model_name = model if model.startswith("models/") else f"models/{model}"

                gemini_model = genai.GenerativeModel(trans_model_name)
                response = gemini_model.generate_content(f"{system_prompt}\n\nText:\n{user_prompt}")
                return response.text.strip()
            except Exception as e:
                print(f"Gemini Translation Error: {e}")
                return text # Fallback to original

        # OpenAI
        try:
            # Use gpt-4o for high quality translation
            trans_model = "gpt-4o"
            response = self.client.chat.completions.create(
                model=trans_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI Translation Error: {e}")
            return text

    def translate_segments_batch(self, segments, target_lang, model="gpt-4o"):
        """
        批次翻譯 segments 列表，保持時間軸對應。
        Input segments: [{'start': 1.0, 'end': 2.0, 'text': 'Hello'}, ...]
        Output segments: [{'start': 1.0, 'end': 2.0, 'text': '你好'}, ...]
        """
        if not segments:
            return []

        lang_name_map = {
            "zh-tw": "Traditional Chinese (Taiwan)",
            "en": "English",
            "zh": "Traditional Chinese",
            "ja": "Japanese"
        }
        target_lang_name = lang_name_map.get(target_lang.lower(), target_lang)

        # Extract texts
        texts = [seg['text'].replace('\n', ' ') for seg in segments]
        
        # We need to process in chunks if too many segments, but gpt-4o can handle large context.
        # Let's try to do it in one go for small/medium files, or chunks of 50 lines.
        # For reliability, chunk size = 30
        CHUNK_SIZE = 30
        translated_texts = []
        
        for i in range(0, len(texts), CHUNK_SIZE):
            chunk = texts[i:i + CHUNK_SIZE]
            
            # Format as numbered list to ensure alignment
            prompt_text = "\n".join([f"{idx}. {text}" for idx, text in enumerate(chunk)])
            
            system_prompt = f"""You are a professional subtitle translator. Translate the following lines into natural, fluent {target_lang_name}.
Rules:
1. Maintain the exact same number of lines.
2. Maintain the exact same line numbers/IDs.
3. specific medical/technical terms should be translated accurately.
4. Output format: Number. Translated Text (e.g. "0. 你好")
5. Do NOT merge lines. One input line = One output line.
"""
            
            user_prompt = f"Lines to translate:\n{prompt_text}"
            
            try:
                # Use translate_text logic (or call API directly)
                # We can reuse client.chat.completions
                # 使用傳入的 model 參數，預設為 gpt-4o
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3
                )
                result = response.choices[0].message.content.strip()
                
                # Parse result
                lines = result.split('\n')
                chunk_map = {}
                for line in lines:
                    # Match "0. Text" or "0.Text"
                    import re
                    match = re.match(r"(\d+)\.\s*(.*)", line)
                    if match:
                        idx = int(match.group(1))
                        content = match.group(2)
                        chunk_map[idx] = content
                
                # Fill translated_texts based on index
                for j in range(len(chunk)):
                    translated_texts.append(chunk_map.get(j, chunk[j])) # Fallback to original if missing
                    
            except Exception as e:
                print(f"Batch Translation Error (Chunk {i}): {e}")
                translated_texts.extend(chunk) # Fallback

        # Re-assemble segments
        translated_segments = []
        for i, seg in enumerate(segments):
            new_seg = seg.copy()
            new_seg['text'] = translated_texts[i] if i < len(translated_texts) else seg['text']
            translated_segments.append(new_seg)
            
        return translated_segments

    def transcribe(
        self,
        audio_path,
        model="gpt-4o-transcribe",
        language="zh",
        output_format="text",
        auto_convert=True,
        segment_duration=600,
        request_timeout=90,
        translate_langs=None,
        cleanup=False,
        progress_callback=None,
    ):
        """主要轉錄功能，處理所有邏輯

        progress_callback: Optional[Callable[[str, float], None]]
            If provided, called with (status_message, fraction 0.0-1.0) at each stage.
        """
        def _emit(msg, frac):
            if progress_callback:
                try:
                    progress_callback(msg, frac)
                except Exception:
                    pass

        _emit("檢查音頻格式與大小", 0.0)
        self.log_stage("檢查音頻格式與大小")

        process_path = audio_path
        temp_files = []
        temp_dirs = []

        parts_dir = None

        if translate_langs is None:
            translate_langs = []

        try:
            ext = Path(process_path).suffix.lower()
            if ext in self.VIDEO_FORMATS:
                _emit("從影片擷取音訊中…", 0.02)
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

            # 智慧格式轉換：只在格式不支援或非高相容性格式時才轉換
            # 高相容性格式 (.mp3, .m4a, .wav) 可直接使用，節省轉換時間
            needs_convert = not audio_info['supported']
            if auto_convert and audio_info['extension'] not in self.HIGH_COMPAT_FORMATS:
                needs_convert = True

            if needs_convert:
                print("\n需要轉換音頻格式...")
                self.log_stage("轉換為高相容性 MP3 格式")
                _emit("轉換為高相容性 MP3…", 0.05)
                convert_dir = tempfile.mkdtemp()
                temp_dirs.append(convert_dir)
                process_path = self.convert_to_compatible_format(process_path, convert_dir)
                temp_files.append(process_path)
                audio_info = self.check_audio_format(process_path)
            else:
                print("\n格式相容，跳過轉換步驟")

            duration = self.get_audio_duration(process_path)
            if duration:
                print(f"  音訊長度: {duration:.1f} 秒 ({duration/60:.1f} 分鐘)")

            needs_split = audio_info['too_large']
            if duration and segment_duration:
                needs_split = needs_split or duration > segment_duration

            final_text_map = {'original': ""}
            for lang in translate_langs:
                final_text_map[lang] = ""

            # 初始化分段轉錄列表（用於大檔案分段處理）
            all_transcripts = []

            if needs_split:
                print(f"\n檔案需要分段處理（每段 {segment_duration/60:.1f} 分鐘）...")
                self.log_stage("音檔過大，開始分段轉錄")
                _emit("切割音檔中…", 0.08)

                # 使用 persistent splitting
                segments, parts_dir = self.split_audio(process_path, segment_duration=segment_duration)
                total_segments = len(segments)

                # 建立 transcripts 目錄
                transcripts_dir = Path(parts_dir) / "transcripts"
                transcripts_dir.mkdir(parents=True, exist_ok=True)

                # Context passing variable
                last_transcript_tail = None

                for i, segment in enumerate(segments):
                    # Reserve 0.10..0.95 for segment progress; each segment advances 1/N of that band
                    _seg_start_frac = 0.10 + 0.85 * (i / total_segments)
                    _emit(f"轉錄第 {i+1}/{total_segments} 段…", _seg_start_frac)
                    segment_path = Path(segment['path'])
                    segment_name = segment_path.stem # e.g. segment_000
                    
                    # Original Transcript File
                    transcript_file = transcripts_dir / f"{segment_name}.txt"
                    transcript_json_file = transcripts_dir / f"{segment_name}.json"
                    
                    print(f"\n處理第 {i+1}/{len(segments)} 段...")
                    
                    segment_data = {
                        'start': segment['start'],
                        'duration': segment['duration'],
                        'text': "",
                        'segments': [] # Store detailed segments with timestamps
                    }
                    
                    # 1. Get Original Transcript (Load or Transcribe)
                    msg_prefix = f"第 {i+1}/{len(segments)} 段"
                    
                    if transcript_json_file.exists() and transcript_json_file.stat().st_size > 0:
                        print(f"✓ [{msg_prefix}] 發現已存檔原文(JSON)，跳過轉錄")
                        import json
                        with open(transcript_json_file, "r", encoding="utf-8") as f:
                            saved_data = json.load(f)
                            segment_data['text'] = saved_data.get('text', "")
                            segment_data['segments'] = saved_data.get('segments', [])
                    elif transcript_file.exists() and transcript_file.stat().st_size > 0:
                         # Legacy fallback
                        print(f"✓ [{msg_prefix}] 發現已存檔原文(Text)，跳過轉錄")
                        with open(transcript_file, "r", encoding="utf-8") as f:
                            segment_data['text'] = f.read()
                    else:
                        self.log_stage(f"{msg_prefix} 上傳並轉錄")
                        try:
                            # Pass context if available
                            transcript = self.transcribe_file(
                                segment['path'],
                                model,
                                language,
                                "text",
                                request_timeout=request_timeout,
                                prompt_context=last_transcript_tail
                            )
                            
                            transcript_text = ""
                            detailed_segments = []
                            
                            if hasattr(transcript, 'text'):
                                transcript_text = transcript.text
                            elif isinstance(transcript, dict):
                                transcript_text = transcript.get('text', "")
                            else:
                                transcript_text = str(transcript)
                                
                            # Extract detailed segments if available (OpenAI json format)
                            if hasattr(transcript, 'segments'):
                                detailed_segments = transcript.segments
                            elif isinstance(transcript, dict) and 'segments' in transcript:
                                detailed_segments = transcript['segments']
                            
                            # === Repetition Loop 偵測 ===
                            rep = self.detect_repetition(transcript_text)
                            if rep['has_repetition']:
                                print(f"⚠️  [{msg_prefix}] 偵測到重複迴圈！"
                                      f"（重複 {rep['repeat_count']}x，佔 {rep['repeat_ratio']:.0%}）")
                                print(f"    重複片段: \"{rep['repeated_phrase'][:60]}...\"")
                                print(f"    已截斷重複部分，保留有效內容 "
                                      f"({len(rep['clean_text'])}/{len(transcript_text)} chars)")
                                transcript_text = rep['clean_text']

                            # Save text transcript
                            with open(transcript_file, "w", encoding="utf-8") as f:
                                f.write(transcript_text)

                            # Save JSON transcript (with timestamps)
                            import json
                            with open(transcript_json_file, "w", encoding="utf-8") as f:
                                json.dump({
                                    'text': transcript_text,
                                    'segments': detailed_segments,
                                    'repetition_detected': rep['has_repetition'],
                                }, f, ensure_ascii=False)

                            print(f"✓ [{msg_prefix}] 轉錄已儲存")
                            segment_data['text'] = transcript_text
                            segment_data['segments'] = detailed_segments
                            
                        except Exception as e:
                            print(f"✗ [{msg_prefix}] 轉錄失敗: {e}")
                            raise e

                    # Update context for next segment
                    # Keep last ~200 chars to avoid token limits but provide continuity
                    if segment_data['text']:
                        current_text = segment_data['text'].strip()
                        last_transcript_tail = current_text[-200:] if len(current_text) > 200 else current_text

                    # 2. Translate (Load or Translate)
                    for lang in translate_langs:
                        trans_file = transcripts_dir / f"{segment_name}_{lang}.txt"
                        if trans_file.exists() and trans_file.stat().st_size > 0:
                            print(f"✓ [{msg_prefix}] 發現已存檔翻譯 ({lang})")
                            with open(trans_file, "r", encoding="utf-8") as f:
                                segment_data[lang] = f.read()
                        else:
                            # Only translate if we have original text
                            if segment_data['text']:
                                print(f"→ [{msg_prefix}] 翻譯中 ({lang})...")
                                trans_text = self.translate_text(segment_data['text'], lang, model)
                                with open(trans_file, "w", encoding="utf-8") as f:
                                    f.write(trans_text)
                                segment_data[lang] = trans_text

                    all_transcripts.append(segment_data)
                    _emit(f"完成 {i+1}/{total_segments} 段", 0.10 + 0.85 * ((i + 1) / total_segments))

                # Merge Logic for all keys
                # We need to handle this per language
                keys_to_merge = ['original'] + translate_langs
                
                # Helper to extract text for a specific key from structure
                # segment_data structure: {'text': orig, 'en': en_text, 'zh-tw': ...}
                # So key 'original' maps to 'text', others map to themselves
                
                merged_results = {} # language -> final string

                for key in keys_to_merge:
                    data_key = 'text' if key == 'original' else key
                    
                    if output_format == "srt":
                        # Try to build precise SRT
                        precise_segments = []
                        has_detailed = False
                        
                        # Collect all DETAILED segments from original
                        for seg in all_transcripts:
                            offset = seg['start']
                            # We MUST use original segments as source of truth for timing
                            if 'segments' in seg and seg['segments']:
                                has_detailed = True
                                for detailed in seg['segments']:
                                    d_start = detailed['start'] if isinstance(detailed, dict) else detailed.start
                                    d_end = detailed['end'] if isinstance(detailed, dict) else detailed.end
                                    d_text = detailed['text'] if isinstance(detailed, dict) else detailed.text
                                    
                                    precise_segments.append({
                                        'start': offset + d_start,
                                        'end': offset + d_end,
                                        'text': d_text
                                    })
                        
                        if has_detailed:
                             if key == 'original':
                                 merged_results[key] = self.generate_srt_from_precise(precise_segments)
                             else:
                                 # High-Precision Translation
                                 print(f"[Precision] Aligning and translating segments for {key}...")
                                 translated_segments = self.translate_segments_batch(precise_segments, key, model)
                                 merged_results[key] = self.generate_srt_from_precise(translated_segments)
                                 
                             continue

                    # Fallback or Translation (if no detailed segments or format != srt)
                    # Extract list of {text, start, duration} for this specific language
                    lang_segments = []
                    for seg in all_transcripts:
                        if data_key in seg:
                            lang_segments.append({
                                'text': seg[data_key],
                                'start': seg['start'],
                                'duration': seg['duration']
                            })
                    
                    if output_format == "srt":
                        merged_results[key] = self.generate_srt_from_segments(lang_segments)
                    else:
                         merged_results[key] = "\n\n".join([s['text'] for s in lang_segments])

                # Assign to final_text (original) and return full map if needed?
                # The method returns final_text, but now we have multiple.
                # We will write files inside this method if they are extra langs, 
                # OR return a dict. But existing caller expects a string.
                # Let's write EXTRA files here and return ORIGINAL string.
                
                final_text = merged_results['original'] # For return
                
                final_text_map = merged_results
                
            else:
                # No Split
                print("\n開始轉錄...")
                self.log_stage("上傳音檔並等待模型回應")
                _emit("上傳音檔並等待模型回應…", 0.30)
                
                # If SRT, request json format for timestamps
                resp_format = "json" if output_format == "srt" else "text"
                
                transcript = self.transcribe_file(
                    process_path,
                    model,
                    language,
                    resp_format, # Use corrected output format
                    request_timeout=request_timeout,
                )
                
                final_text = ""
                
                if hasattr(transcript, 'text'):
                     final_text = transcript.text
                elif isinstance(transcript, dict):
                     final_text = transcript.get('text', "")
                else:
                     final_text = str(transcript)
                
                self.log_stage("模型回應已取得")

                # === Repetition Loop 偵測（單檔模式）===
                rep = self.detect_repetition(final_text)
                if rep['has_repetition']:
                    print(f"⚠️  偵測到重複迴圈！"
                          f"（重複 {rep['repeat_count']}x，佔 {rep['repeat_ratio']:.0%}）")
                    print(f"    重複片段: \"{rep['repeated_phrase'][:60]}...\"")
                    print(f"    已截斷重複部分，保留有效內容 "
                          f"({len(rep['clean_text'])}/{len(final_text)} chars)")
                    final_text = rep['clean_text']

                final_text_map['original'] = final_text
                
                # Check for precise segments availability
                precise_segments = []
                if output_format == "srt":
                    # Check if we got detailed segments
                    detailed_segments = []
                    if hasattr(transcript, 'segments'):
                        detailed_segments = transcript.segments
                    elif isinstance(transcript, dict) and 'segments' in transcript:
                        detailed_segments = transcript['segments']
                    
                    if detailed_segments:
                         # Convert to standard format
                         for ds in detailed_segments:
                             d_start = ds['start'] if isinstance(ds, dict) else ds.start
                             d_end = ds['end'] if isinstance(ds, dict) else ds.end
                             d_text = ds['text'] if isinstance(ds, dict) else ds.text
                             precise_segments.append({'start': d_start, 'end': d_end, 'text': d_text})
                         
                         final_text_map['original'] = self.generate_srt_from_precise(precise_segments)

                # Translate 
                for lang in translate_langs:
                     if precise_segments and output_format == "srt":
                         # Use high precision batch translation
                         print(f"[Precision] Aligning and translating segments for {lang}...")
                         trans_segs = self.translate_segments_batch(precise_segments, lang, model)
                         final_text_map[lang] = self.generate_srt_from_precise(trans_segs)
                     else:
                         # Fallback text translation
                         final_text_map[lang] = self.translate_text(final_text, lang, model)

            # Post-Process (Markdown/SRT Fallback) for ALL languages
            for key in final_text_map:
                txt = final_text_map[key]
                # If key is original and we already generated SRT (list/str), skip processing if it looks like SRT
                if output_format == "srt" and (txt.startswith("1\n") or "-->" in txt[:50]):
                     continue

                if output_format == "markdown":
                     # Add header ?
                     final_text_map[key] = f"# 語音轉錄結果 ({key})\n\n{txt}\n"
                elif output_format == "srt":
                     # If it's single chunk and API gave text, convert to SRT fallback
                     if isinstance(txt, str) and not txt.strip() == "":
                         final_text_map[key] = self.generate_srt_fallback(txt)

            self.log_stage("整理輸出內容")
            _emit("整理輸出內容…", 0.98)

            if not needs_split:
                 print(f"\n轉錄完成！總字數：{len(final_text_map['original'])} 字元")
            else:
                total_duration = sum(seg['duration'] for seg in all_transcripts if isinstance(seg, dict))
                print("\n轉錄完成！")
                print(f"  處理時長：{total_duration:.1f} 秒 ({total_duration/60:.1f} 分鐘)")
                if parts_dir:
                     if cleanup:
                         print(f"  正在清理暫存檔案：{parts_dir}")
                         try:
                             shutil.rmtree(parts_dir)
                             print("  ✓ 暫存檔案已清理")
                         except Exception as e:
                             print(f"  ⚠️ 清理失敗: {e}")
                     else:
                         print(f"  暫存檔案保留於：{parts_dir}")

            _emit("完成", 1.0)
            return final_text_map

        except Exception as e:
            raise Exception(f"轉錄失敗: {str(e)}")

        finally:
            for tmp_file in temp_files:
                if tmp_file and os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except OSError:
                        pass
            # We explicitly DO NOT remove parts_dir here to support inspection and resume.
            # User can manually delete it if they want.

                
    def generate_srt_from_precise(self, segments):
        """從精確的 segment 資訊 (start, end, text) 生成 SRT"""
        srt_content = []
        for i, segment in enumerate(segments):
            start_srt = self.format_srt_time(segment['start'])
            end_srt = self.format_srt_time(segment['end'])
            text = segment['text'].strip()
            
            srt_content.append(f"{i+1}")
            srt_content.append(f"{start_srt} --> {end_srt}")
            srt_content.append(text)
            srt_content.append("")
            
        return "\n".join(srt_content)

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
                       help="選擇模型 (例如 gpt-4o-mini-transcribe, gemini-2.0-flash-exp)")
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
    parser.add_argument("--translate", help="翻譯語言，用逗號分隔 (例如: en,zh-tw)")
    parser.add_argument("--cleanup", action="store_true", help="完成後清理暫存檔案")
    
    args = parser.parse_args()

    if args.max_segment_seconds <= 0:
        print("錯誤：max-segment-seconds 需為正整數")
        sys.exit(1)
        
    translate_langs = []
    if args.translate:
        translate_langs = [l.strip() for l in args.translate.split(',') if l.strip()]
        print(f"啟用翻譯模式：{translate_langs}")
    
    # 檢查 API key
    if "gemini" not in args.model.lower():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("錯誤：使用 OpenAI 模型請設定環境變數 OPENAI_API_KEY")
            sys.exit(1)
    else:
        # Check Gemini Key
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
             print("錯誤：使用 Gemini 模型請設定環境變數 GEMINI_API_KEY 或 GOOGLE_API_KEY")
             sys.exit(1)
        api_key = "dummy" # Placeholder to satisfy __init__
        
    # 檢查 ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except:
        print("警告：未找到 ffmpeg，某些功能可能無法使用")
        print("請安裝 ffmpeg: brew install ffmpeg")
        
    # 執行轉錄
    try:
        transcriber = AudioTranscriber(api_key)
        final_result_map = transcriber.transcribe(
            args.audio_file,
            model=args.model,
            language=args.language,
            output_format=args.format,
            auto_convert=not args.no_convert,
            segment_duration=args.max_segment_seconds,
            request_timeout=args.request_timeout,
            translate_langs=translate_langs,
            cleanup=args.cleanup
        )
        
        # 處理輸出
        # final_result_map 是一個字典: {'original': ..., 'en': ..., 'zh-tw': ...}
        # 如果 output_format 是字串 (舊行為)，它是 original
        
        if isinstance(final_result_map, str):
            # Backward compatibility (should not happen with new code but safe guard)
            final_result_map = {'original': final_result_map}

        # 決定基礎輸出檔案路徑
        base_output_path = args.output
        
        # 如果沒指定 output，使用 stdout (僅輸出 original)
        if not base_output_path:
             print("\n" + "="*60)
             print("轉錄結果 (Original)：")
             print("="*60)
             print(final_result_map['original'])
             
             for lang in translate_langs:
                 if lang in final_result_map:
                     print(f"\n" + "="*60)
                     print(f"轉錄結果 ({lang})：")
                     print("="*60)
                     print(final_result_map[lang])
             return

        # 有指定 output，處理各語言檔案
        output_path_obj = Path(base_output_path)
        # 如果有副檔名，先分離
        # e.g. /path/to/myvideo.txt -> stem=myvideo, suffix=.txt
        #      /path/to/myvideo -> stem=myvideo, suffix=""
        
        stem = output_path_obj.stem
        parent = output_path_obj.parent
        # 如果使用者透過 args.output 傳入完整檔名 (e.g. out.srt)，我們就用這個當 original
        # 翻譯版則插入語言代碼: out_en.srt
        
        # 根據 format 決定副檔名 (如果使用者沒給)
        suffix = output_path_obj.suffix
        if not suffix:
             ext_map = {
                "text": ".txt",
                "markdown": ".md",
                "srt": ".srt"
             }
             suffix = ext_map.get(args.format, ".txt")
        
        for key, text in final_result_map.items():
            if not text:
                continue
                
            if key == 'original':
                final_path = parent / f"{stem}{suffix}"
            else:
                final_path = parent / f"{stem}_{key}{suffix}"
                
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✓ [{key}] 結果已儲存到：{final_path}")
            
    except Exception as e:
        print(f"\n錯誤：{e}")
        # Print traceback for easier debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
