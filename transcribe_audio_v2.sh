#!/bin/bash

# Improved Voice Transcription Script V2 (Smart Resume)
# Features: Recursive directory processing, Interactive model/format selection, Per-file resume capability
#
# Difference from v1:
# This version checks if the specific output file exists for EACH file.
# If it exists, it skips that single file but continues to process other files in the same directory.
# This allows for resuming interrupted jobs.
# 主要差異
# 舊版 (v1)：看到資料夾內有轉錄檔 -> 跳過整個資料夾。
# 新版 (v2)：看到資料夾內有 video.txt -> 跳過這一個；看到 audio.txt 沒產生 -> 繼續執行這一個。
# 執行後：
# 請選擇 1) MP3 only (避免重複轉 video)。
# 請選擇您要的輸出格式 (例如 SRT)。
# 它會自動掃描，看到已做完的顯示 Skipping ...，沒做完的會顯示 Transcribing ... 並開始工作。

set -u
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ENTRY="$SCRIPT_DIR/gpt4o_transcribe_improved.py"
DEFAULT_TARGET="."

MODEL_OPTIONS=(
  "gpt-4o-mini-transcribe"
  "gpt-4o-transcribe"
  "gemini-3-flash-preview"
  "gemini-2.5-flash"
)

FORMAT_OPTIONS=(
  "text"
  "markdown"
  "srt"
)

# AUDIO_EXTENSIONS will be set in prompt_file_type_selection

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
    echo "✓ Detected virtual environment: ${VIRTUAL_ENV}"
    return
  fi

  if [ -d "$SCRIPT_DIR/venv" ]; then
    echo "Activating virtual environment: ${SCRIPT_DIR}/venv"
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "✓ Activated virtual environment: ${VIRTUAL_ENV}"
  else
    echo "⚠️  No virtual environment (venv) found, using system Python"
  fi
}

prompt_model_selection() {
  local choice
  while true; do
    echo "Select Model to Use:"
    echo "  1) gpt-4o-mini-transcribe (Fast/Cost-effective) - RECOMMENDED"
    echo "  2) gpt-4o-transcribe (High Quality)"
    echo "  3) gemini-3-flash-preview (Gemini 3 Flash)"
    echo "  4) gemini-2.5-flash (Gemini 2.5 Flash)"
    read -rp "Enter number (Default 1): " choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) SELECTED_MODEL="${MODEL_OPTIONS[0]}"; break ;;
      2) SELECTED_MODEL="${MODEL_OPTIONS[1]}"; break ;;
      3) SELECTED_MODEL="${MODEL_OPTIONS[2]}"; break ;;
      4) SELECTED_MODEL="${MODEL_OPTIONS[3]}"; break ;;
      *) echo "Invalid input, please try again." ;;
    esac
  done
  echo "→ Selected Model: ${SELECTED_MODEL}"
  print_divider
}

prompt_format_selection() {
  local choice
  while true; do
    echo "Select Output Format:"
    echo "  1) text (Plain Text)"
    echo "  2) markdown (Markdown)"
    echo "  3) srt (Subtitles)"
    read -rp "Enter number (Default 1): " choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) SELECTED_FORMAT="${FORMAT_OPTIONS[0]}"; break ;;
      2) SELECTED_FORMAT="${FORMAT_OPTIONS[1]}"; break ;;
      3) SELECTED_FORMAT="${FORMAT_OPTIONS[2]}"; break ;;
      *) echo "Invalid input, please try again." ;;
    esac
  done
  echo "→ Selected Output Format: ${SELECTED_FORMAT}"
  print_divider
}

prompt_file_type_selection() {
  local choice
  while true; do
    echo "Select File Types to Process:"
    echo "  1) MP3 only (Recommended: Avoid double-billing for videos)"
    echo "  2) All supported formats (mp3, mp4, wav, m4a...)"
    read -rp "Enter number (Default 1): " choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) AUDIO_EXTENSIONS=(mp3); echo "→ Limited to: MP3 only"; break ;;
      2) AUDIO_EXTENSIONS=(mp3 mp4 mpeg mpga m4a wav webm); echo "→ Enabled: All supported formats"; break ;;
      *) echo "Invalid input, please try again." ;;
    esac
  done
  print_divider
}

prompt_bilingual_selection() {
  local choice
  
  # Determine readable source language name
  local source_lang_name="Original"
  case "$SELECTED_LANGUAGE" in
    zh) source_lang_name="Traditional Chinese" ;;
    en) source_lang_name="English" ;;
    ja) source_lang_name="Japanese" ;;
    *) source_lang_name="Original ($SELECTED_LANGUAGE)" ;;
  esac

  while true; do
    echo "Enable Bilingual Output?"
    echo "  Reference: Source Audio is set to [$source_lang_name]"
    echo "  1) No (Output: $source_lang_name only)"
    echo "  2) Yes (Output: $source_lang_name + English + Traditional Chinese)"
    read -rp "Enter number (Default 1): " choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) TRANSLATE_ARGS=""; echo "→ Bilingual Mode: Disabled"; break ;;
      2) TRANSLATE_ARGS="--translate en,zh-tw"; echo "→ Bilingual Mode: Enabled (en, zh-tw)"; break ;;
      *) echo "Invalid input, please try again." ;;
    esac
  done
  print_divider
}

prompt_cleanup() {
  echo "Cleanup intermediate files (segments) after success?"
  echo "  1) Yes (Recommended for clean output)"
  echo "  2) No  (Keep for debug/resume later)"
  read -rp "Enter number (Default 1): " choice
  [ -z "$choice" ] && choice=1
  case "$choice" in
    1) CLEANUP_ARGS="--cleanup"; echo "→ Cleanup: Enabled";;
    2) CLEANUP_ARGS=""; echo "→ Cleanup: Disabled";;
    *) CLEANUP_ARGS="--cleanup"; echo "→ Cleanup: Enabled (Default)";;
  esac
  print_divider
}

prompt_language_selection() {
  local choice
  while true; do
    echo "Select Source Audio Language:"
    echo "  1) Traditional Chinese (Default - zh)"
    echo "  2) English (en)"
    echo "  3) Japanese (ja)"
    echo "  4) Custom code"
    read -rp "Enter number (Default 1): " choice
    [ -z "$choice" ] && choice=1
    case "$choice" in
      1) SELECTED_LANGUAGE="zh"; echo "→ Language: Traditional Chinese"; break ;;
      2) SELECTED_LANGUAGE="en"; echo "→ Language: English"; break ;;
      3) SELECTED_LANGUAGE="ja"; echo "→ Language: Japanese"; break ;;
      4) 
        read -rp "Enter language code (e.g. fr, es, ko): " custom_lang
        SELECTED_LANGUAGE="$custom_lang"
        echo "→ Language: $SELECTED_LANGUAGE"
        break 
        ;;
      *) echo "Invalid input, please try again." ;;
    esac
  done
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
    echo "Error: Target file or directory not found: ${raw_target}" >&2
    exit 1
  fi
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
      printf '\r%s Transcribing... Elapsed: %d s' "${spinner_sequence[$spinner_index]}" "$elapsed"
      spinner_index=$(((spinner_index + 1) % ${#spinner_sequence[@]}))
    fi
  done

  printf '\r%-50s\r' ""
}

run_transcription() {
  local audio_file="$1"
  local output_file
  output_file="$(build_output_path "$audio_file")"

  # SMART RESUME CHECK
  if [ -f "$output_file" ]; then
    echo "→ Skipping: ${audio_file}" 
    echo "  (Reason: Output file already exists: $(basename "$output_file"))"
    # printf '\n'
    return 2 # Special return code for skipped
  fi

  echo "▶︎ Transcribing: ${audio_file}"
  python "$PYTHON_ENTRY" "$audio_file" \
    --model "$SELECTED_MODEL" \
    --language "$SELECTED_LANGUAGE" \
    --format "$SELECTED_FORMAT" \
    --max-segment-seconds "$SEGMENT_SECONDS" \
    --request-timeout "$REQUEST_TIMEOUT" \
    --output "$output_file" \
    $TRANSLATE_ARGS \
    $CLEANUP_ARGS &
  local cmd_pid=$!
  local interrupted=0

  trap 'interrupted=1; kill "$cmd_pid" 2>/dev/null' INT TERM

  show_progress_until_done "$cmd_pid"
  wait "$cmd_pid"
  local status=$?
  trap - INT TERM

  if [ $interrupted -ne 0 ]; then
    echo "✗ Transcription interrupted by user: ${audio_file}" >&2
    print_divider
    exit 130
  fi

  if [ $status -eq 0 ]; then
    echo "✓ Done. Output: ${output_file}"
    # If bilingual, print extra
    if [ -n "$TRANSLATE_ARGS" ]; then
        echo "  (Also generated translated versions if requested)"
    fi
    print_divider
    return 0
  else
    echo "✗ Transcription failed: ${audio_file}" >&2
    print_divider
    return 1
  fi
}

process_single_file() {
  local file="$1"
  # Single file mode doesn't need to check directory skip logic, 
  # but run_transcription will still check if output exists.
  
  run_transcription "$file"
  local ret=$?
  
  if [ $ret -eq 0 ]; then
      PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
  elif [ $ret -eq 2 ]; then
      SKIPPED_FILE_COUNT=$((SKIPPED_FILE_COUNT + 1))
  else
      FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
}

process_directory() {
  local target_dir="$1"
  local found_any=0

  # Build find arguments
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
    
    # We REMOVED the whole-directory skipping logic (should_skip_dir) here.
    # We rely on run_transcription to check file-by-file.

    run_transcription "$audio_file"
    local ret=$?

    if [ $ret -eq 0 ]; then
      PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
    elif [ $ret -eq 2 ]; then
      SKIPPED_FILE_COUNT=$((SKIPPED_FILE_COUNT + 1))
    else
      FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
  done < <(find "${find_args[@]}")

  if [ $found_any -eq 0 ]; then
    echo "⚠️  No supported audio files found in: ${target_dir}"
  fi
}

main() {
  print_divider
  echo "Voice Transcription Tool V2 (Smart Resume + Bilingual)"
  print_divider

  load_dotenv_file
  activate_virtualenv
  prompt_model_selection
  prompt_language_selection
  prompt_format_selection
  prompt_file_type_selection
  prompt_bilingual_selection
  prompt_cleanup

  local target_input="${1:-}";

  local target_input="${1:-}";
  resolve_target_path "$target_input"

  local segment_minutes
  segment_minutes=$((SEGMENT_SECONDS / 60))
  if [ $segment_minutes -eq 0 ]; then
    segment_minutes=1
  fi
  echo "Max segment duration: ${SEGMENT_SECONDS}s (~${segment_minutes} min)"

  PROCESSED_COUNT=0
  SKIPPED_FILE_COUNT=0
  FAILED_COUNT=0

  if [ "$TARGET_KIND" = "file" ]; then
    process_single_file "$TARGET_PATH"
  else
    process_directory "$TARGET_PATH"
  fi

  echo "Processing Complete."
  echo "  Successful: ${PROCESSED_COUNT} files"
  echo "  Skipped (Already exists): ${SKIPPED_FILE_COUNT} files"
  if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "  Failed: ${FAILED_COUNT} files"
  fi
}

main "$@"
