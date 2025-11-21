#!/bin/bash

# 改良版語音轉錄腳本：支援資料夾遞迴處理、互動式模型/格式選擇

set -u
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ENTRY="$SCRIPT_DIR/gpt4o_transcribe_improved.py"
DEFAULT_TARGET="."

MODEL_OPTIONS=(
  "gpt-4o-transcribe"
  "gpt-4o-mini-transcribe"
  "whisper-1"
)

FORMAT_OPTIONS=(
  "text"
  "markdown"
  "srt"
)

AUDIO_EXTENSIONS=(mp3 mp4 mpeg mpga m4a wav webm)

SEGMENT_SECONDS="${TRANSCRIBE_SEGMENT_SECONDS:-600}"
REQUEST_TIMEOUT="${TRANSCRIBE_REQUEST_TIMEOUT:-90}"

if ! [[ "$SEGMENT_SECONDS" =~ ^[0-9]+$ ]] || [ "$SEGMENT_SECONDS" -le 0 ]; then
  SEGMENT_SECONDS=600
fi

load_dotenv_file() {
  local env_file="$SCRIPT_DIR/.env"
  if [ -f "$env_file" ]; then
    # shellcheck disable=SC1090
    set -a
    source "$env_file"
    set +a
  fi
}

print_divider() {
  printf '\n%s\n' "========================================"
}

activate_virtualenv() {
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "✓ 已偵測到虛擬環境：${VIRTUAL_ENV}"
    return
  fi

  if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "正在啟動虛擬環境：${SCRIPT_DIR}/venv"
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "✓ 已啟動虛擬環境：${VIRTUAL_ENV}"
  else
    echo "⚠️  未找到虛擬環境 (venv)，將使用系統 Python"
  fi
}

prompt_model_selection() {
  local choice
  while true; do
    echo "選擇要使用的模型："
    echo "  1) gpt-4o-transcribe (高品質)"
    echo "  2) gpt-4o-mini-transcribe (快速/省成本)"
    echo "  3) whisper-1 (Whisper 模型)"
    read -rp "請輸入數字 (預設 1)：" choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) SELECTED_MODEL="${MODEL_OPTIONS[0]}"; break ;;
      2) SELECTED_MODEL="${MODEL_OPTIONS[1]}"; break ;;
      3) SELECTED_MODEL="${MODEL_OPTIONS[2]}"; break ;;
      *) echo "輸入無效，請重新選擇。" ;;
    esac
  done
  echo "→ 已選擇模型：${SELECTED_MODEL}"
  print_divider
}

prompt_format_selection() {
  local choice
  while true; do
    echo "選擇輸出格式："
    echo "  1) text (純文字)"
    echo "  2) markdown (Markdown)"
    echo "  3) srt (字幕)"
    read -rp "請輸入數字 (預設 1)：" choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) SELECTED_FORMAT="${FORMAT_OPTIONS[0]}"; break ;;
      2) SELECTED_FORMAT="${FORMAT_OPTIONS[1]}"; break ;;
      3) SELECTED_FORMAT="${FORMAT_OPTIONS[2]}"; break ;;
      *) echo "輸入無效，請重新選擇。" ;;
    esac
  done
  echo "→ 已選擇輸出格式：${SELECTED_FORMAT}"
  print_divider
}

resolve_target_path() {
  local raw_target="$1"

  if [ -z "$raw_target" ]; then
    raw_target="$DEFAULT_TARGET"
  fi

  if [ -d "$raw_target" ]; then
    TARGET_PATH="$(cd "$raw_target" 2>/dev/null && pwd)"
    TARGET_KIND="directory"
  elif [ -f "$raw_target" ]; then
    local dir
    dir="$(cd "$(dirname "$raw_target")" 2>/dev/null && pwd)"
    TARGET_PATH="$dir/$(basename "$raw_target")"
    TARGET_KIND="file"
  else
    local normalized
    normalized="$(normalize_path_guess "$raw_target")"
    if [ -n "$normalized" ] && [ -e "$normalized" ]; then
      resolve_target_path "$normalized"
      return
    fi
    echo "錯誤：找不到指定的檔案或資料夾：${raw_target}" >&2
    exit 1
  fi
}

should_skip_dir() {
  local dir="$1"
  if find "$dir" -maxdepth 1 -mindepth 1 -exec basename {} \; 2>/dev/null | \
      grep -qiE 'transcript|轉錄|逐字稿'; then
    return 0
  fi
  return 1
}

build_output_path() {
  local audio_file="$1"
  local base="${audio_file%.*}"
  case "$SELECTED_FORMAT" in
    text) echo "${base}_transcript.txt" ;;
    markdown) echo "${base}_transcript.md" ;;
    srt) echo "${base}_transcript.srt" ;;
    *) echo "${base}_transcript.txt" ;;
  esac
}

normalize_path_guess() {
  local raw="$1"
  python - "$raw" <<'PY'
import os
import sys

raw = sys.argv[1]

def sanitize(name: str) -> str:
    stripped = name.replace(';', '')
    return ' '.join(stripped.split())

if os.path.exists(raw):
    print(raw)
    sys.exit(0)

is_abs = os.path.isabs(raw)

if is_abs:
    current = '/'
    parts = [p for p in raw.split('/') if p]
else:
    current = os.getcwd()
    parts = [p for p in raw.split('/') if p and p != '.']

for part in parts:
    candidate = os.path.join(current, part)
    if os.path.exists(candidate):
        current = candidate
        continue

    if not os.path.isdir(current):
        current = ''
        break

    target_key = sanitize(part)
    match = None
    try:
        entries = os.listdir(current)
    except OSError:
        current = ''
        break

    for entry in entries:
        if sanitize(entry) == target_key:
            match = entry
            break

    if match is None:
        current = ''
        break

    current = os.path.join(current, match)

if current and os.path.exists(current):
    print(os.path.abspath(current))
else:
    print('')
PY
}

show_progress_until_done() {
  local pid="$1"
  local start_ts
  start_ts=$(date +%s)
  local spinner_sequence=('|' '/' '-' '\\')
  local spinner_index=0

  while kill -0 "$pid" 2>/dev/null; do
    sleep 1 || break
    if kill -0 "$pid" 2>/dev/null; then
      local now
      now=$(date +%s)
      local elapsed=$((now - start_ts))
      printf '\r%s 轉錄中... 已等待 %d 秒' "${spinner_sequence[$spinner_index]}" "$elapsed"
      spinner_index=$(((spinner_index + 1) % ${#spinner_sequence[@]}))
    fi
  done

  printf '\r%-50s\r' ""
}

run_transcription() {
  local audio_file="$1"
  local output_file
  output_file="$(build_output_path "$audio_file")"

  echo "▶︎ 正在轉錄：${audio_file}"
  python "$PYTHON_ENTRY" "$audio_file" \
    --model "$SELECTED_MODEL" \
    --format "$SELECTED_FORMAT" \
    --max-segment-seconds "$SEGMENT_SECONDS" \
    --request-timeout "$REQUEST_TIMEOUT" \
    --output "$output_file" &
  local cmd_pid=$!
  local interrupted=0

  trap 'interrupted=1; kill "$cmd_pid" 2>/dev/null' INT TERM

  show_progress_until_done "$cmd_pid"
  wait "$cmd_pid"
  local status=$?
  trap - INT TERM

  if [ $interrupted -ne 0 ]; then
    echo "✗ 轉錄已被使用者中斷：${audio_file}" >&2
    print_divider
    exit 130
  fi

  if [ $status -eq 0 ]; then
    echo "✓ 完成，輸出檔案：${output_file}"
    print_divider
    return 0
  else
    echo "✗ 轉錄失敗：${audio_file}" >&2
    print_divider
    return 1
  fi
}

process_single_file() {
  local file="$1"
  local dir
  dir="$(dirname "$file")"

  if [ "${TARGET_KIND:-}" != "file" ] && should_skip_dir "$dir"; then
    echo "略過資料夾：${dir}（已偵測到 transcript 相關檔案）"
    return
  fi

  if [ "${TARGET_KIND:-}" = "file" ]; then
    local output_file
    output_file="$(build_output_path "$file")"

    echo "▶︎ 正在轉錄：${file}"
    python "$PYTHON_ENTRY" "$file" \
      --model "$SELECTED_MODEL" \
      --format "$SELECTED_FORMAT" \
      --max-segment-seconds "$SEGMENT_SECONDS" \
      --request-timeout "$REQUEST_TIMEOUT" \
      --output "$output_file"
    local status=$?

    if [ $status -eq 0 ]; then
      echo "✓ 完成，輸出檔案：${output_file}"
      print_divider
      PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
    else
      echo "✗ 轉錄失敗：${file}" >&2
      print_divider
      FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    return
  fi

  if run_transcription "$file"; then
    PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
  else
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
}

process_directory() {
  local target_dir="$1"
  local skipped_dirs=""
  local found_any=0

  # 組合 find 條件
  local -a find_args
  find_args=("$target_dir" "-type" "f" "(")
  local first=1
  for ext in "${AUDIO_EXTENSIONS[@]}"; do
    if [ $first -eq 0 ]; then
      find_args+=("-o")
    fi
    find_args+=("-iname" "*.${ext}")
    first=0
  done
  find_args+=(")" "-print0")

  while IFS= read -r -d '' audio_file; do
    found_any=1
    local dir
    dir="$(dirname "$audio_file")"

    if should_skip_dir "$dir"; then
      if ! printf '%s\n' "$skipped_dirs" | grep -Fxq "$dir"; then
        echo "略過資料夾：${dir}（已偵測到 transcript 相關檔案）"
        if [ -z "$skipped_dirs" ]; then
          skipped_dirs="$dir"
        else
          skipped_dirs="$skipped_dirs\n$dir"
        fi
        SKIPPED_DIR_COUNT=$((SKIPPED_DIR_COUNT + 1))
      fi
      continue
    fi

    if run_transcription "$audio_file"; then
      PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
    else
      FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
  done < <(find "${find_args[@]}")

  if [ $found_any -eq 0 ]; then
    echo "⚠️  找不到任何支援的音訊檔案於：${target_dir}"
  fi
}

main() {
  print_divider
  echo "語音轉錄工具 (資料夾/子資料夾自動處理)"
  print_divider

  load_dotenv_file
  activate_virtualenv
  prompt_model_selection
  prompt_format_selection

  local target_input="${1:-}";
  resolve_target_path "$target_input"

  local segment_minutes
  segment_minutes=$((SEGMENT_SECONDS / 60))
  if [ $segment_minutes -eq 0 ]; then
    segment_minutes=1
  fi
  echo "每段最長時長：${SEGMENT_SECONDS} 秒 (~${segment_minutes} 分鐘)"

  PROCESSED_COUNT=0
  SKIPPED_DIR_COUNT=0
  FAILED_COUNT=0

  if [ "$TARGET_KIND" = "file" ]; then
    process_single_file "$TARGET_PATH"
  else
    process_directory "$TARGET_PATH"
  fi

  echo "處理完成。"
  echo "  成功轉錄：${PROCESSED_COUNT} 檔"
  if [ "$TARGET_KIND" = "directory" ]; then
    echo "  略過資料夾：${SKIPPED_DIR_COUNT} 個"
  fi
  if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "  失敗：${FAILED_COUNT} 檔"
  fi
}

main "$@"
