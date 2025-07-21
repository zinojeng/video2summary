#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批次處理工具選單
提供友善的介面來選擇和執行各種批次處理任務
"""

import os
import sys
import subprocess
from pathlib import Path

# 設定顏色
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    """清除螢幕"""
    os.system('clear' if os.name == 'posix' else 'cls')

def print_header():
    """顯示標題"""
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("="*80)
    print("                      批次處理工具選單 v1.0")
    print("                   Batch Processing Tools Menu")
    print("="*80)
    print(f"{Colors.ENDC}")

def print_menu():
    """顯示主選單"""
    print(f"{Colors.CYAN}📋 請選擇要執行的任務：{Colors.ENDC}\n")
    
    print(f"{Colors.YELLOW}【1. 投影片處理】Slide Processing{Colors.ENDC}")
    print("  1.1 - 批次捕獲投影片 (從影片中提取投影片)")
    print("  1.2 - 批次分析投影片 (使用 AI 分析投影片內容)")
    print("  1.3 - 分析完整投影片資料夾 (處理無 selected_slides 的資料夾)")
    
    print(f"\n{Colors.YELLOW}【2. 音頻轉錄處理】Audio Transcription{Colors.ENDC}")
    print("  2.1 - 批次處理轉錄文件 (生成詳細演講筆記)")
    print("  2.2 - 繼續處理剩餘轉錄文件")
    
    print(f"\n{Colors.YELLOW}【3. 合併工具】Merge Tools{Colors.ENDC}")
    print("  3.1 - 合併演講筆記與投影片分析")
    
    print(f"\n{Colors.YELLOW}【4. 報告工具】Reports{Colors.ENDC}")
    print("  4.1 - 生成轉錄筆記處理報告")
    print("  4.2 - 生成合併筆記最終報告")
    
    print(f"\n{Colors.YELLOW}【5. 進階工具】Advanced Tools{Colors.ENDC}")
    print("  5.1 - 恢復中斷的批次處理 (OpenAI)")
    print("  5.2 - 恢復中斷的批次處理 (Gemini)")
    
    print(f"\n{Colors.RED}  0 - 退出程式{Colors.ENDC}")

def get_api_key(service):
    """獲取 API 金鑰"""
    api_key = os.getenv(f"{service.upper()}_API_KEY")
    if not api_key:
        print(f"\n{Colors.YELLOW}請輸入 {service} API Key:{Colors.ENDC}")
        api_key = input().strip()
    return api_key

def run_script(script_path, args=None):
    """執行 Python 腳本"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n{Colors.GREEN}✅ 執行完成！{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.RED}❌ 執行失敗：{e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ 使用者中斷執行{Colors.ENDC}")
    
    input("\n按 Enter 鍵返回選單...")

def main():
    """主程式"""
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        choice = input(f"\n{Colors.GREEN}請輸入選項編號: {Colors.ENDC}")
        
        if choice == '0':
            print(f"\n{Colors.CYAN}感謝使用！再見！{Colors.ENDC}")
            break
            
        elif choice == '1.1':
            # 批次捕獲投影片
            print(f"\n{Colors.CYAN}批次捕獲投影片{Colors.ENDC}")
            path = input("請輸入影片路徑或資料夾路徑: ").strip()
            recursive = input("是否遞迴搜尋子資料夾? (y/n) [n]: ").strip().lower() == 'y'
            auto_select = input("是否自動選擇最佳投影片? (y/n) [n]: ").strip().lower() == 'y'
            
            args = [path]
            if recursive:
                args.append('--recursive')
            if auto_select:
                args.append('--auto-select')
            
            run_script('batch_processing/slides_analysis/batch_slide_capture.py', args)
            
        elif choice == '1.2':
            # 批次分析投影片
            print(f"\n{Colors.CYAN}批次分析投影片{Colors.ENDC}")
            base_path = input("請輸入基礎路徑 (如 /path/to/ADA2025): ").strip()
            api_key = get_api_key('OPENAI')
            
            args = [base_path, api_key]
            run_script('batch_processing/slides_analysis/batch_slides_analysis.py', args)
            
        elif choice == '1.3':
            # 分析完整投影片資料夾
            print(f"\n{Colors.CYAN}分析完整投影片資料夾{Colors.ENDC}")
            base_path = input("請輸入基礎路徑: ").strip()
            api_key = get_api_key('OPENAI')
            
            args = [base_path, api_key]
            run_script('batch_processing/slides_analysis/batch_process_full_slides.py', args)
            
        elif choice == '2.1':
            # 批次處理轉錄文件
            print(f"\n{Colors.CYAN}批次處理轉錄文件{Colors.ENDC}")
            base_path = input("請輸入基礎路徑: ").strip()
            api_key = get_api_key('GEMINI')
            
            args = [base_path, api_key]
            run_script('batch_processing/transcription_notes/batch_transcription_notes_v2.py', args)
            
        elif choice == '2.2':
            # 繼續處理剩餘轉錄文件
            print(f"\n{Colors.CYAN}繼續處理剩餘轉錄文件{Colors.ENDC}")
            base_path = input("請輸入基礎路徑: ").strip()
            api_key = get_api_key('GEMINI')
            
            args = [base_path, api_key]
            run_script('batch_processing/transcription_notes/continue_transcription_notes.py', args)
            
        elif choice == '3.1':
            # 合併演講筆記與投影片分析
            print(f"\n{Colors.CYAN}合併演講筆記與投影片分析{Colors.ENDC}")
            base_path = input("請輸入基礎路徑: ").strip()
            api_key = get_api_key('GEMINI')
            
            args = [base_path, api_key]
            run_script('batch_processing/merge_tools/merge_notes_slides.py', args)
            
        elif choice == '4.1':
            # 生成轉錄筆記處理報告
            print(f"\n{Colors.CYAN}生成轉錄筆記處理報告{Colors.ENDC}")
            run_script('batch_processing/reports/transcription_notes_final_report.py')
            
        elif choice == '4.2':
            # 生成合併筆記最終報告
            print(f"\n{Colors.CYAN}生成合併筆記最終報告{Colors.ENDC}")
            run_script('batch_processing/reports/merge_notes_final_report.py')
            
        elif choice == '5.1':
            # 恢復中斷的批次處理 (OpenAI)
            print(f"\n{Colors.CYAN}恢復中斷的批次處理 (OpenAI){Colors.ENDC}")
            api_key = get_api_key('OPENAI')
            
            args = [api_key]
            run_script('batch_processing/batch_process_resume_openai.py', args)
            
        elif choice == '5.2':
            # 恢復中斷的批次處理 (Gemini)
            print(f"\n{Colors.CYAN}恢復中斷的批次處理 (Gemini){Colors.ENDC}")
            api_key = get_api_key('GEMINI')
            
            args = [api_key]
            run_script('batch_processing/batch_process_resume.py', args)
            
        else:
            print(f"\n{Colors.RED}無效的選項！{Colors.ENDC}")
            input("按 Enter 鍵繼續...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}程式已退出。{Colors.ENDC}")
        sys.exit(0)