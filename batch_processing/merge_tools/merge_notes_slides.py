#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
合併演講筆記與投影片分析
將演講者內容與投影片內容整合成更詳細的二合一筆記
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import google.generativeai as genai
from datetime import datetime


def setup_gemini(api_key: str):
    """設置 Gemini API"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model


def find_matching_files(base_path: str) -> List[Tuple[Path, Path, Path]]:
    """查找同時有演講筆記和投影片分析的文件夾"""
    matches = []
    
    # 查找所有演講筆記
    for notes_file in Path(base_path).rglob('transcription-*_detailed_notes.md'):
        if notes_file.name.startswith('._'):
            continue
            
        folder = notes_file.parent
        
        # 查找對應的投影片分析文件
        slides_analysis = None
        
        # 優先查找 selected_slides_analysis.md
        for slides_folder in folder.rglob('*_slides'):
            selected_analysis = slides_folder / 'selected_slides_analysis.md'
            if selected_analysis.exists():
                slides_analysis = selected_analysis
                break
        
        # 如果沒有 selected_slides_analysis.md，查找其他分析文件
        if not slides_analysis:
            for slides_folder in folder.rglob('*_slides'):
                for analysis_file in ['slides_analysis.md', 'selected_slides_analysis_gemini.md', 'slides_analysis_gemini.md']:
                    candidate = slides_folder / analysis_file
                    if candidate.exists():
                        slides_analysis = candidate
                        break
                if slides_analysis:
                    break
        
        if slides_analysis:
            matches.append((folder, notes_file, slides_analysis))
    
    return matches


def read_content(file_path: Path) -> str:
    """讀取文件內容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"讀取文件錯誤 {file_path}: {e}")
        return ""


def merge_notes_with_slides(
    model,
    speaker_notes: str,
    slides_analysis: str,
    session_title: str
) -> Tuple[bool, str, Dict]:
    """使用 Gemini 合併演講筆記與投影片分析"""
    
    prompt = f"""請將以下演講筆記與投影片分析合併成一份更詳細的二合一筆記。

要求：
1. **以演講者內容為主軸**，保持原有的演講流程和結構
2. 在相關段落中加入投影片參考，格式：**(參見 Slide X)**
3. 當投影片包含演講中未詳述的內容時，在該段落下方用 __底線標記__ 補充說明
4. 避免重複內容，只補充新的資訊或更清楚的解釋
5. 保持原有的階層結構和重點標記
6. 投影片中的圖表、數據或公式等視覺元素，用文字描述補充
7. 建立演講內容與投影片的對應關係

會議標題：{session_title}

---

演講筆記內容：
{speaker_notes[:40000]}

---

投影片分析內容：
{slides_analysis[:20000]}

---

請生成合併後的詳細筆記（使用繁體中文）。記住：
- 以演講者內容為主軸
- 投影片內容作為補充和增強
- 用底線標記延伸解讀
- 建立清晰的內容對應關係
"""
    
    try:
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
        print("用法: python merge_notes_slides.py <base_path> <gemini_api_key>")
        sys.exit(1)
    
    base_path = sys.argv[1]
    api_key = sys.argv[2]
    
    print("\n📝 批次合併演講筆記與投影片分析")
    print("="*60)
    print(f"使用模型: Gemini 2.5 Pro")
    print(f"處理路徑: {base_path}")
    print("="*60)
    
    # 設置 Gemini
    model = setup_gemini(api_key)
    
    # 查找匹配的文件
    matches = find_matching_files(base_path)
    print(f"\n找到 {len(matches)} 個同時有演講筆記和投影片分析的文件夾")
    
    if not matches:
        print("未找到任何匹配的文件")
        return
    
    # 顯示找到的匹配
    print("\n匹配的文件：")
    for i, (folder, notes, slides) in enumerate(matches[:5], 1):
        print(f"{i}. {folder.name}")
        print(f"   演講筆記: {notes.name}")
        print(f"   投影片分析: {slides.parent.name}/{slides.name}")
    if len(matches) > 5:
        print(f"... 還有 {len(matches) - 5} 個文件夾")
    
    # 載入進度
    progress_file = 'merge_notes_progress.json'
    progress = load_progress(progress_file)
    
    # 開始處理
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for i, (folder, notes_file, slides_file) in enumerate(matches, 1):
        folder_path = str(folder)
        
        # 檢查是否已處理
        if folder_path in progress['processed']:
            print(f"\n[{i}/{len(matches)}] 已處理過: {folder.name}")
            continue
        
        print(f"\n[{i}/{len(matches)}] 處理: {folder.name}")
        
        try:
            # 讀取內容
            print("  讀取演講筆記...")
            speaker_notes = read_content(notes_file)
            
            print("  讀取投影片分析...")
            slides_analysis = read_content(slides_file)
            
            if not speaker_notes or not slides_analysis:
                print("  ⚠️  文件內容為空，跳過")
                continue
            
            print(f"  演講筆記長度: {len(speaker_notes)} 字符")
            print(f"  投影片分析長度: {len(slides_analysis)} 字符")
            
            # 合併內容
            print("  生成合併筆記...")
            success, merged_content, info = merge_notes_with_slides(
                model,
                speaker_notes,
                slides_analysis,
                folder.name
            )
            
            if success:
                # 保存合併筆記
                output_file = notes_file.with_name(
                    notes_file.stem.replace('_detailed_notes', '_merged_notes')
                )
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {folder.name} - 演講與投影片綜合筆記\n\n")
                    f.write(f"*整合自演講筆記與投影片分析*\n\n")
                    f.write(f"*生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                    f.write(f"*演講筆記來源：{notes_file.name}*\n")
                    f.write(f"*投影片分析來源：{slides_file.parent.name}/{slides_file.name}*\n\n")
                    f.write("---\n\n")
                    f.write(merged_content)
                
                print(f"  ✅ 合併筆記已保存: {output_file.name}")
                progress['processed'].append(folder_path)
                processed_count += 1
                
                # 更新統計
                if 'total_tokens' not in progress['stats']:
                    progress['stats']['total_tokens'] = 0
                progress['stats']['total_tokens'] += info.get('prompt_tokens', 0) + info.get('completion_tokens', 0)
                
            else:
                print(f"  ❌ 處理失敗: {merged_content}")
                progress['failed'].append({
                    'folder': folder_path,
                    'error': merged_content,
                    'timestamp': datetime.now().isoformat()
                })
                failed_count += 1
            
            # 保存進度
            save_progress(progress_file, progress)
            
            # 顯示進度
            if i < len(matches):
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                eta = avg_time * (len(matches) - i)
                print(f"\n進度: {i}/{len(matches)} ({i/len(matches)*100:.1f}%)")
                print(f"預計剩餘時間: {eta/60:.1f} 分鐘")
            
            # 延遲
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用戶中斷！進度已保存。")
            save_progress(progress_file, progress)
            break
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            progress['failed'].append({
                'folder': folder_path,
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
    print(f"總共處理: {len(progress['processed'])} 個文件夾")
    print(f"總用時: {total_time/60:.1f} 分鐘")
    
    if processed_count > 0:
        print(f"平均處理時間: {total_time/processed_count:.1f} 秒/文件夾")
    
    if 'total_tokens' in progress['stats']:
        print(f"總 Token 使用: {progress['stats']['total_tokens']:,}")
    
    print(f"\n✅ 批次處理完成！")
    print(f"合併筆記已保存為: *_merged_notes.md")
    print(f"進度文件: {progress_file}")


if __name__ == "__main__":
    main()