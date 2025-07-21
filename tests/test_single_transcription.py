#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
測試單個轉錄文件處理
"""

import os
import sys
import re
from pathlib import Path
import google.generativeai as genai
from datetime import datetime


def setup_gemini(api_key: str):
    """設置 Gemini API"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model


def read_srt_file(file_path: str) -> str:
    """讀取 SRT 文件並提取純文本"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    
    return ' '.join(text_lines)


def find_agenda_file(folder_path: str) -> tuple:
    """查找議程文件"""
    folder = Path(folder_path)
    
    # 查找各種格式的議程文件
    for ext in ['*.rtfd', '*.rtf', '*.docx', '*.doc']:
        files = list(folder.glob(ext))
        for f in files:
            if not f.name.startswith('._') and 'transcription' not in f.name.lower():
                return str(f), f.name
    
    return None, None


def extract_rtfd_content(rtfd_path: str) -> str:
    """從 RTFD 文件夾中提取內容"""
    rtfd_folder = Path(rtfd_path)
    if rtfd_folder.is_dir():
        rtf_file = rtfd_folder / 'TXT.rtf'
        if rtf_file.exists():
            with open(rtf_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # 簡單提取文本
                text = re.sub(r'\\par\s*', '\n', content)
                text = re.sub(r'\\tab\s*', '\t', text)
                text = re.sub(r'\\[a-z]+\d*\s?', '', text)
                text = re.sub(r'[{}]', '', text)
                return text[:3000]
    return ""


def main():
    if len(sys.argv) < 2:
        print("用法: python test_single_transcription.py <gemini_api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # 測試文件路徑
    test_file = "/Volumes/WD_BLACK/國際年會/ADA2025/Advancing Effective and Equitable Treatment of Hyperglycemia in Pregnancy/transcription-4.srt"
    
    print("\n📝 測試單個轉錄文件處理")
    print("="*60)
    
    if not os.path.exists(test_file):
        print(f"❌ 文件不存在: {test_file}")
        return
    
    # 設置 Gemini
    model = setup_gemini(api_key)
    
    # 獲取文件信息
    file_path = Path(test_file)
    parent_folder = file_path.parent
    session_title = parent_folder.name
    
    print(f"會議標題: {session_title}")
    print(f"轉錄文件: {file_path.name}")
    
    # 讀取轉錄內容
    print("\n讀取轉錄內容...")
    transcription_content = read_srt_file(test_file)
    print(f"轉錄內容長度: {len(transcription_content)} 字符")
    print(f"前100字符: {transcription_content[:100]}...")
    
    # 查找議程文件
    print("\n查找議程文件...")
    agenda_file, agenda_name = find_agenda_file(str(parent_folder))
    agenda_content = None
    
    if agenda_file:
        print(f"找到議程文件: {agenda_name}")
        if agenda_file.endswith('.rtfd'):
            agenda_content = extract_rtfd_content(agenda_file)
        else:
            # 處理其他格式
            with open(agenda_file, 'r', encoding='utf-8', errors='ignore') as f:
                agenda_content = f.read()[:3000]
        
        if agenda_content:
            print(f"議程內容長度: {len(agenda_content)} 字符")
            print(f"議程前100字符: {agenda_content[:100]}...")
    else:
        print("未找到議程文件")
    
    # 構建 Gemini 提示詞
    print("\n準備生成詳細筆記...")
    
    prompt = f"""請將以下演講轉錄內容整理成詳細的筆記。

要求：
1. **不是摘要**，而是完整整理演講者的內容
2. 保留演講者的所有重要觀點、數據、案例和細節
3. 進行修飾潤稿，修正語音轉錄錯誤，使內容更專業易讀
4. 使用清晰的階層結構組織內容
5. 對重點使用 **粗體**、*斜體* 或 __底線__ 標記
6. 保持專業術語的準確性（特別是醫學術語）
7. 如果有多位演講者，明確標示每位演講者的內容
8. 保留重要的數據、統計資料和研究發現

會議標題：{session_title}

"""
    
    if agenda_content:
        prompt += f"""
議程內容：
{agenda_content}

請根據上述議程的結構來組織演講內容，讓筆記結構與議程對應。

"""
    
    prompt += f"""
轉錄內容：
{transcription_content[:30000]}  

請生成詳細的演講筆記（使用繁體中文）。記住：這不是摘要，而是完整的演講內容整理，要儘可能保留演講者的所有重要內容。
"""
    
    print(f"提示詞長度: {len(prompt)} 字符")
    
    # 調用 Gemini API
    print("\n調用 Gemini API...")
    try:
        response = model.generate_content(prompt)
        
        if response.text:
            # 保存結果
            output_file = file_path.with_name(f"{file_path.stem}_detailed_notes_test.md")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {session_title} - 詳細演講筆記\n\n")
                f.write(f"*基於音頻轉錄文件生成：{file_path.name}*\n\n")
                f.write(f"*生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                if agenda_file:
                    f.write(f"*參考議程：{agenda_name}*\n\n")
                f.write("---\n\n")
                f.write(response.text)
            
            print(f"\n✅ 成功！筆記已保存到: {output_file}")
            print(f"生成內容長度: {len(response.text)} 字符")
            
            # 顯示前500字符預覽
            print("\n筆記內容預覽：")
            print("="*60)
            print(response.text[:500])
            print("="*60)
            
        else:
            print("❌ Gemini 沒有返回內容")
            
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")


if __name__ == "__main__":
    main()