#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自動繼續處理剩餘的轉錄文件
"""

import os
import sys
import json
import time
from pathlib import Path
from batch_transcription_notes_v2 import (
    setup_gemini, read_transcription_file, find_agenda_file, 
    extract_agenda_from_file, process_transcription_with_gemini,
    save_progress, load_progress
)
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("用法: python auto_continue_transcription.py <base_path> <gemini_api_key>")
        sys.exit(1)
    
    base_path = sys.argv[1]
    api_key = sys.argv[2]
    
    print("\n📝 自動繼續處理剩餘的轉錄文件")
    print("="*60)
    
    # 設置 Gemini
    model = setup_gemini(api_key)
    
    # 載入進度
    progress_file = 'transcription_notes_progress_v2.json'
    progress = load_progress(progress_file)
    
    print(f"已處理: {len(progress['processed'])} 個文件")
    print(f"已使用 Token: {progress['stats'].get('total_tokens', 0):,}")
    
    # 查找剩餘的 SRT 文件
    srt_files = list(Path(base_path).rglob('transcription*.srt'))
    srt_files = [f for f in srt_files if not f.name.startswith('._')]
    
    # 過濾出未處理的文件
    remaining_files = []
    for srt_file in srt_files:
        srt_path = str(srt_file)
        txt_path = str(srt_file.with_suffix('.txt'))
        
        # 如果 .txt 和 .srt 都沒處理過，加入待處理列表
        if srt_path not in progress['processed'] and txt_path not in progress['processed']:
            remaining_files.append(srt_file)
    
    print(f"剩餘待處理: {len(remaining_files)} 個文件\n")
    
    if not remaining_files:
        print("✅ 所有文件都已處理完成！")
        return
    
    # 開始處理
    start_time = time.time()
    processed_count = 0
    failed_count = 0
    
    for i, trans_file in enumerate(remaining_files, 1):
        trans_path = str(trans_file)
        
        # 獲取會議標題
        parent_folder = trans_file.parent
        session_title = parent_folder.name
        
        print(f"\n[{i}/{len(remaining_files)}] 處理: {session_title}")
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
            agenda_file = find_agenda_file(str(parent_folder), trans_file.stem)
            if agenda_file:
                print(f"  找到議程文件: {os.path.basename(agenda_file)}")
                agenda_content = extract_agenda_from_file(agenda_file)
                if agenda_content and len(agenda_content) > 50:
                    print(f"  議程內容長度: {len(agenda_content)} 字符")
            
            # 處理轉錄內容
            success, notes_content, info = process_transcription_with_gemini(
                model, 
                transcription_content,
                agenda_content,
                session_title
            )
            
            if success:
                # 保存筆記
                output_file = trans_file.with_name(f"{trans_file.stem}_detailed_notes.md")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {session_title} - 詳細演講筆記\n\n")
                    f.write(f"*基於音頻轉錄文件生成：{trans_file.name}*\n\n")
                    f.write(f"*生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                    if agenda_file:
                        f.write(f"*參考議程：{os.path.basename(agenda_file)}*\n\n")
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
            
            # 顯示進度
            elapsed = time.time() - start_time
            if i < len(remaining_files):
                avg_time = elapsed / i
                eta = avg_time * (len(remaining_files) - i)
                print(f"\n進度: {i}/{len(remaining_files)} ({i/len(remaining_files)*100:.1f}%)")
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


if __name__ == "__main__":
    main()