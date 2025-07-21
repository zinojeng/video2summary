#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批次處理音頻轉錄文件，生成詳細筆記
使用 Gemini API 進行內容整理和潤稿
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
from datetime import datetime


def setup_gemini(api_key: str):
    """設置 Gemini API"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model


def read_transcription_file(file_path: str) -> str:
    """讀取轉錄文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 如果是 SRT 文件，去除時間戳
    if file_path.endswith('.srt'):
        # 移除 SRT 格式的序號和時間戳
        lines = content.split('\n')
        text_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # 跳過序號
            if line.isdigit():
                i += 1
                # 跳過時間戳
                if i < len(lines) and '-->' in lines[i]:
                    i += 1
                # 收集文本
                while i < len(lines) and lines[i].strip() != '':
                    text_lines.append(lines[i].strip())
                    i += 1
            i += 1
        content = ' '.join(text_lines)
    
    return content


def find_agenda_files(folder_path: str) -> Optional[str]:
    """查找議程文件（docx, rtf, txt）"""
    folder = Path(folder_path)
    for ext in ['*.docx', '*.rtf', '*.txt']:
        agenda_files = list(folder.glob(ext))
        if agenda_files:
            # 優先選擇包含會議標題的文件
            for f in agenda_files:
                if not f.name.startswith('._') and 'transcription' not in f.name.lower():
                    return str(f)
    return None


def extract_agenda_from_file(file_path: str) -> str:
    """從文件中提取議程信息"""
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()[:2000]  # 限制長度
        elif file_path.endswith('.rtf'):
            # 簡單提取 RTF 中的文本
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # 移除 RTF 控制字符
                text = re.sub(r'\\[a-z]+\d*\s?', '', content)
                text = re.sub(r'[{}]', '', text)
                return text[:2000]
        elif file_path.endswith('.docx'):
            # 如果有 python-docx 可以使用
            try:
                import docx
                doc = docx.Document(file_path)
                text = '\n'.join([para.text for para in doc.paragraphs])
                return text[:2000]
            except:
                return "Agenda file found but cannot read .docx format"
    except Exception as e:
        return f"Error reading agenda: {str(e)}"
    
    return "No agenda content extracted"


def process_transcription_with_gemini(
    model,
    transcription_content: str,
    agenda_content: Optional[str],
    session_title: str
) -> Tuple[bool, str, Dict[str, Any]]:
    """使用 Gemini 處理轉錄內容"""
    
    # 構建提示詞
    prompt = f"""請將以下演講轉錄內容整理成詳細的筆記。

要求：
1. **不是摘要**，而是完整整理演講者的內容
2. 保留演講者的所有重要觀點和細節
3. 進行修飾潤稿，使內容更易讀
4. 使用階層結構組織內容
5. 對重點使用 **粗體**、*斜體* 或 __底線__ 標記
6. 如果有議程，根據議程分段整理
7. 保持專業術語的準確性
8. 修正明顯的語音轉錄錯誤

會議標題：{session_title}

"""
    
    if agenda_content:
        prompt += f"""
議程內容：
{agenda_content}

請根據上述議程來組織內容結構。

"""
    
    prompt += f"""
轉錄內容：
{transcription_content}

請生成詳細的演講筆記（使用繁體中文）：
"""
    
    try:
        # 調用 Gemini API
        response = model.generate_content(prompt)
        
        if response.text:
            return True, response.text, {
                'prompt_tokens': len(prompt),
                'completion_tokens': len(response.text),
                'model': 'gemini-2.5-pro'
            }
        else:
            return False, "No response from Gemini", {}
            
    except Exception as e:
        return False, str(e), {}


def save_progress(progress_file: str, progress: Dict):
    """保存進度"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_progress(progress_file: str) -> Dict:
    """載入進度"""
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'stats': {}}


def main():
    if len(sys.argv) < 3:
        print("用法: python batch_transcription_notes.py <base_path> <gemini_api_key>")
        sys.exit(1)
    
    base_path = sys.argv[1]
    api_key = sys.argv[2]
    
    print("\n📝 批次處理音頻轉錄筆記")
    print("="*60)
    print(f"使用模型: Gemini 2.5 Pro")
    print(f"處理路徑: {base_path}")
    print("="*60)
    
    # 設置 Gemini
    model = setup_gemini(api_key)
    
    # 查找所有轉錄文件
    transcription_files = []
    for pattern in ['transcription*.txt', 'transcription*.srt']:
        transcription_files.extend(Path(base_path).rglob(pattern))
    
    # 過濾掉隱藏文件
    transcription_files = [f for f in transcription_files if not f.name.startswith('._')]
    
    print(f"\n找到 {len(transcription_files)} 個轉錄文件")
    
    if not transcription_files:
        print("未找到任何轉錄文件")
        return
    
    # 載入進度
    progress_file = 'transcription_notes_progress.json'
    progress = load_progress(progress_file)
    
    # 開始處理
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for i, trans_file in enumerate(transcription_files, 1):
        trans_path = str(trans_file)
        
        # 檢查是否已處理
        if trans_path in progress['processed']:
            print(f"\n[{i}/{len(transcription_files)}] 已處理過: {trans_file.name}")
            continue
        
        # 獲取會議標題（從父文件夾名稱）
        parent_folder = trans_file.parent
        session_title = parent_folder.name
        
        print(f"\n[{i}/{len(transcription_files)}] 處理: {session_title}")
        print(f"  文件: {trans_file.name}")
        
        try:
            # 讀取轉錄內容
            transcription_content = read_transcription_file(trans_path)
            
            if not transcription_content or len(transcription_content) < 100:
                print("  ⚠️  轉錄內容太短，跳過")
                continue
            
            print(f"  轉錄長度: {len(transcription_content)} 字符")
            
            # 查找議程文件
            agenda_content = None
            agenda_file = find_agenda_files(str(parent_folder))
            if agenda_file:
                print(f"  找到議程文件: {os.path.basename(agenda_file)}")
                agenda_content = extract_agenda_from_file(agenda_file)
            
            # 處理轉錄內容
            success, notes_content, info = process_transcription_with_gemini(
                model, 
                transcription_content,
                agenda_content,
                session_title
            )
            
            if success:
                # 保存筆記
                output_file = trans_file.with_name(f"{trans_file.stem}_notes.md")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {session_title} - 演講筆記\n\n")
                    f.write(f"*基於音頻轉錄文件生成：{trans_file.name}*\n\n")
                    f.write(f"*生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                    f.write("---\n\n")
                    f.write(notes_content)
                
                print(f"  ✅ 筆記已保存: {output_file.name}")
                progress['processed'].append(trans_path)
                processed_count += 1
                
                # 更新統計
                if 'total_tokens' not in progress['stats']:
                    progress['stats']['total_tokens'] = 0
                progress['stats']['total_tokens'] += info.get('prompt_tokens', 0) + info.get('completion_tokens', 0)
                
            else:
                print(f"  ❌ 處理失敗: {notes_content}")
                progress['failed'].append({
                    'file': trans_path,
                    'error': notes_content,
                    'timestamp': datetime.now().isoformat()
                })
                failed_count += 1
            
            # 保存進度
            save_progress(progress_file, progress)
            
            # 延遲以遵守 API 限制
            time.sleep(3)  # Gemini 2.5 Pro 有較寬鬆的限制
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用戶中斷！進度已保存。")
            save_progress(progress_file, progress)
            break
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            progress['failed'].append({
                'file': trans_path,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            failed_count += 1
            save_progress(progress_file, progress)
    
    # 完成統計
    total_time = time.time() - start_time
    print("\n" + "="*60)
    print("📊 處理完成統計")
    print("="*60)
    print(f"本次處理: {processed_count} 個成功, {failed_count} 個失敗")
    print(f"總共處理: {len(progress['processed'])} 個文件")
    print(f"總用時: {total_time/60:.1f} 分鐘")
    
    if processed_count > 0:
        print(f"平均處理時間: {total_time/processed_count:.1f} 秒/文件")
    
    if 'total_tokens' in progress['stats']:
        print(f"總 Token 使用: {progress['stats']['total_tokens']:,}")
    
    print(f"\n✅ 批次處理完成！")
    print(f"筆記文件已保存為: *_notes.md")
    print(f"進度文件: {progress_file}")


if __name__ == "__main__":
    main()