#!/usr/bin/env bash
# codex-multi-agents-tmux.sh
#
# 功能:
# - 发送标准格式对话到目标会话并写入日志。
# - 按名单初始化角色 tmux 运行环境。
#
# 对应文件:
# - spec: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
# - test: test/codex-multi-agents/test_codex-multi-agents-tmux.py
# - impl: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_LOCK=4
readonly RC_INTERNAL=5

FILE=""
OP_TALK=0
OP_INIT_ENV=0
SESSION_ID=""
FROM=""
TO=""
MESSAGE=""
LOG_FILE=""
AGENTS_FILE=""
AGENT_NAME=""
HAS_SESSION_ID=0
HAS_FROM=0
HAS_TO=0
HAS_MESSAGE=0
HAS_LOG=0
HAS_FILE=0
HAS_NAME=0

trim() {
  local s="${1-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

err() {
  local code="$1"
  shift
  printf "ERROR(%s): %s\n" "$code" "$*" >&2
  exit "$code"
}

usage() {
  cat <<'EOF'
Usage:
  codex-multi-agents-tmux.sh -talk -from <sender> -to <target_name> -session-id <target_session_id> -message <message> -log <log_path>
  codex-multi-agents-tmux.sh -init-env -file <agents_list_path> -name <agent_name>

Examples:
  codex-multi-agents-tmux.sh -talk -from scheduler -to worker-a -session-id worker-a -message "请处理任务 T1" -log ./agents/codex-multi-agents/log/talk.log
  codex-multi-agents-tmux.sh -init-env -file ./agents/codex-multi-agents/agents-lists.md -name 小明

Return codes:
  0 success
  1 argument error
  2 file or environment error
  3 data error
  4 lock error
  5 internal error
EOF
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -talk)
        OP_TALK=1
        shift
        ;;
      -init-env)
        OP_INIT_ENV=1
        shift
        ;;
      -from=*)
        FROM="${1#*=}"
        HAS_FROM=1
        shift
        ;;
      -session-id=*)
        SESSION_ID="${1#*=}"
        HAS_SESSION_ID=1
        shift
        ;;
      -session-id)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -session-id"
        SESSION_ID="$2"
        HAS_SESSION_ID=1
        shift 2
        ;;
      -from)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -from"
        FROM="$2"
        HAS_FROM=1
        shift 2
        ;;
      -to=*)
        TO="${1#*=}"
        HAS_TO=1
        shift
        ;;
      -to)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -to"
        TO="$2"
        HAS_TO=1
        shift 2
        ;;
      -message=*)
        MESSAGE="${1#*=}"
        HAS_MESSAGE=1
        shift
        ;;
      -message)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -message"
        MESSAGE="$2"
        HAS_MESSAGE=1
        shift 2
        ;;
      -log=*)
        LOG_FILE="${1#*=}"
        HAS_LOG=1
        shift
        ;;
      -log)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -log"
        LOG_FILE="$2"
        HAS_LOG=1
        shift 2
        ;;
      -file=*)
        AGENTS_FILE="${1#*=}"
        HAS_FILE=1
        shift
        ;;
      -file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -file"
        AGENTS_FILE="$2"
        HAS_FILE=1
        shift 2
        ;;
      -name=*)
        AGENT_NAME="${1#*=}"
        HAS_NAME=1
        shift
        ;;
      -name)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -name"
        AGENT_NAME="$2"
        HAS_NAME=1
        shift 2
        ;;
      -h|--help)
        usage
        exit "$RC_OK"
        ;;
      *)
        err "$RC_ARG" "unknown argument: $1"
        ;;
    esac
  done

  local op_count=$((OP_TALK + OP_INIT_ENV))
  [[ "$op_count" -eq 1 ]] || err "$RC_ARG" "exactly one operation is required: -talk|-init-env"

  if [[ "$OP_TALK" -eq 1 ]]; then
    [[ "$HAS_FROM" -eq 1 ]] || err "$RC_ARG" "-talk requires -from"
    [[ "$HAS_TO" -eq 1 ]] || err "$RC_ARG" "-talk requires -to"
    [[ "$HAS_SESSION_ID" -eq 1 ]] || err "$RC_ARG" "-talk requires -session-id"
    [[ "$HAS_MESSAGE" -eq 1 ]] || err "$RC_ARG" "-talk requires -message"
    [[ "$HAS_LOG" -eq 1 ]] || err "$RC_ARG" "-talk requires -log"
    [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "empty value for -from"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    [[ -n "$(trim "$SESSION_ID")" ]] || err "$RC_ARG" "empty value for -session-id"
    [[ -n "$(trim "$MESSAGE")" ]] || err "$RC_ARG" "empty value for -message"
    [[ -n "$(trim "$LOG_FILE")" ]] || err "$RC_ARG" "empty value for -log"
    [[ "$HAS_FILE" -eq 0 && "$HAS_NAME" -eq 0 ]] || err "$RC_ARG" "-talk does not accept -file/-name"
  fi

  if [[ "$OP_INIT_ENV" -eq 1 ]]; then
    [[ "$HAS_FILE" -eq 1 ]] || err "$RC_ARG" "-init-env requires -file"
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "-init-env requires -name"
    [[ -n "$(trim "$AGENTS_FILE")" ]] || err "$RC_ARG" "empty value for -file"
    [[ -n "$(trim "$AGENT_NAME")" ]] || err "$RC_ARG" "empty value for -name"
    [[ "$HAS_FROM" -eq 0 && "$HAS_TO" -eq 0 && "$HAS_SESSION_ID" -eq 0 && "$HAS_MESSAGE" -eq 0 && "$HAS_LOG" -eq 0 ]] || err "$RC_ARG" "-init-env does not accept -from/-to/-session-id/-message/-log"
  fi
}

ensure_tmux_available() {
  command -v tmux >/dev/null 2>&1 || err "$RC_FILE" "tmux not found in PATH"
}

tmux_has_session() {
  local target="$1"
  tmux has-session -t "$target" >/dev/null 2>&1
}

format_talk_message() {
  printf "@%s向@%s发起会话: %s" "$FROM" "$TO" "$MESSAGE"
}

acquire_log_lock() {
  local lock_file="${LOG_FILE}.lock"
  exec {lock_fd}> "$lock_file" || err "$RC_LOCK" "cannot open lock file: $lock_file"
  flock -x -w 5 "$lock_fd" || err "$RC_LOCK" "cannot acquire lock: $lock_file"
}

append_log_line() {
  local line="$1"
  local dir
  dir="$(dirname "$LOG_FILE")"
  mkdir -p "$dir" || err "$RC_FILE" "failed to create log directory: $dir"

  acquire_log_lock
  printf "%s\n" "$line" >> "$LOG_FILE" || err "$RC_INTERNAL" "failed to write log file: $LOG_FILE"
}

do_talk() {
  tmux_has_session "$SESSION_ID" || err "$RC_DATA" "target session not found: $SESSION_ID"

  local line
  line="$(format_talk_message)"
  send_tmux_command_once "$SESSION_ID" "$line"
  append_log_line "$line"
  printf "OK: talk %s -> %s (%s)\n" "$FROM" "$TO" "$SESSION_ID"
}

send_tmux_command_once() {
  local session="$1"
  local command_text="$2"
  tmux send-keys -t "$session" "$command_text" || err "$RC_INTERNAL" "tmux send-keys failed: $session"
  sleep 3 || err "$RC_INTERNAL" "sleep failed during command confirm: $command_text"
  tmux send-keys -t "$session" ENTER || err "$RC_INTERNAL" "tmux send-keys failed: $session"
}

resolve_list_script_path() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  printf "%s/codex-multi-agents-list.sh" "$script_dir"
}

find_agent_field() {
  local field="$1"
  local list_script
  local value
  list_script="$(resolve_list_script_path)"
  [[ -x "$list_script" ]] || err "$RC_FILE" "list script not executable: $list_script"

  if ! value="$(bash "$list_script" -file "$AGENTS_FILE" -find -name "$AGENT_NAME" -key "$field" 2>/dev/null)"; then
    err "$RC_DATA" "failed to read field '$field' for agent: $AGENT_NAME"
  fi
  printf "%s" "$value"
}

find_startup_type() {
  local list_script
  local value
  list_script="$(resolve_list_script_path)"
  [[ -x "$list_script" ]] || err "$RC_FILE" "list script not executable: $list_script"

  if value="$(bash "$list_script" -file "$AGENTS_FILE" -find -name "$AGENT_NAME" -key "启动设置" 2>/dev/null)"; then
    printf "%s" "$value"
    return 0
  fi
  if value="$(bash "$list_script" -file "$AGENTS_FILE" -find -name "$AGENT_NAME" -key "启动类型" 2>/dev/null)"; then
    printf "%s" "$value"
    return 0
  fi
  err "$RC_DATA" "failed to read startup type for agent: $AGENT_NAME"
}

do_init_env() {
  [[ -e "$AGENTS_FILE" ]] || err "$RC_FILE" "file not found: $AGENTS_FILE"
  [[ -f "$AGENTS_FILE" ]] || err "$RC_FILE" "not a regular file: $AGENTS_FILE"
  [[ -r "$AGENTS_FILE" ]] || err "$RC_FILE" "file is not readable: $AGENTS_FILE"

  local session
  local startup_type
  local agent_session
  session="$(find_agent_field "会话")"
  startup_type="$(find_startup_type)"
  agent_session="$(find_agent_field "agent session")"

  [[ -n "$(trim "$session")" ]] || err "$RC_DATA" "empty session for agent: $AGENT_NAME"

  if ! tmux_has_session "$session"; then
    tmux new-session -d -s "$session" || err "$RC_INTERNAL" "tmux new-session failed: $session"
  fi

  if [[ "$startup_type" == "codex" ]]; then
    [[ -n "$(trim "$agent_session")" ]] || err "$RC_DATA" "empty agent session for codex agent: $AGENT_NAME"
    send_tmux_command_once "$session" "codex"
    sleep 3 || err "$RC_INTERNAL" "sleep failed during init step: codex->rename"
    send_tmux_command_once "$session" "/rename $agent_session"
  fi

  printf "OK: init-env %s (%s)\n" "$AGENT_NAME" "$session"
}

main() {
  parse_args "$@"
  ensure_tmux_available

  if [[ "$OP_TALK" -eq 1 ]]; then
    do_talk
  elif [[ "$OP_INIT_ENV" -eq 1 ]]; then
    do_init_env
  else
    err "$RC_INTERNAL" "unexpected operation state"
  fi
}

main "$@"
