#!/usr/bin/env bash
# codex-multi-agents-task.sh
#
# 创建者: 榕
# 最后一次更改: 神秘人
#
# 功能:
# - 管理 TODO.md 任务流转: 分发、完成、暂停、继续、改派、新建。
# - 支持 DONE.md 自动创建与完成记录追加。
# - 在分发、完成、暂停、继续时同步更新 agents-lists.md 角色状态。
# - 在分发时可选调用 tmux 对话脚本，向目标角色发送任务消息。
# - 在分发前固定调用一次 list 的 -init，更新目标角色信息并提醒其同步自身提示词信息。
# - 写操作统一使用 flock 文件锁。
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-task.md
# - test: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-task.py
# - impl: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh

set -u
set -o pipefail

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_LOCK=4
readonly RC_INTERNAL=5

OP_DISPATCH=0
OP_DONE=0
OP_PAUSE=0
OP_CONTINUE=0
OP_REASSIGN=0
OP_NEW=0
OP_STATUS=0

FILE=""
AGENTS_LIST=""
TASK_ID=""
TO=""
FROM=""
INFO=""
LOG_FILE=""
WORKTREE=""
MESSAGE=""

HAS_FILE=0
HAS_AGENTS_LIST=0
HAS_TASK_ID=0
HAS_TO=0
HAS_FROM=0
HAS_INFO=0
HAS_LOG=0
HAS_WORKTREE=0
HAS_MESSAGE=0
HAS_DOING=0
HAS_TASK_LIST=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LIST_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-list.sh"
TMUX_SCRIPT="${SCRIPT_DIR}/codex-multi-agents-tmux.sh"
DEFAULT_CONFIG_FILE="${REPO_ROOT}/agents/codex-multi-agents/config/config.txt"

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
  cat <<'USAGE'
Usage:
  codex-multi-agents-task.sh -file <TODO.md> -dispatch -task_id <id> -to <worker> -agents-list <agents-lists.md> [-message <text>]
  codex-multi-agents-task.sh -file <TODO.md> -done -task_id <id> -log <log_path> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -pause -task_id <id> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -continue -task_id <id> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -reassign -task_id <id> -to <worker> -agents-list <agents-lists.md>
  codex-multi-agents-task.sh -file <TODO.md> -new -info <desc> [-to <worker>] [-from <owner>] [-worktree <path>] [-log <record_path>]
  codex-multi-agents-task.sh -file <TODO.md> -status -doing
  codex-multi-agents-task.sh -file <TODO.md> -status -task-list

Examples:
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -dispatch -task_id EX-3 -to worker-a -agents-list ./agents/codex-multi-agents/agents-lists.md -message "请处理任务 EX-3"
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -done -task_id EX-1 -log ./agents/codex-multi-agents/log/task-EX-1.log -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -pause -task_id EX-2 -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -continue -task_id EX-2 -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -reassign -task_id EX-2 -to worker-c -agents-list ./agents/codex-multi-agents/agents-lists.md
  codex-multi-agents-task.sh -file ./skills/codex-multi-agents/examples/TODO.md -new -info "补充单元测试" -to worker-b -from 李白 -worktree repo-x -log ./log/record.md
  codex-multi-agents-task.sh ./skills/codex-multi-agents/examples/TODO.md -file -status -doing
  codex-multi-agents-task.sh ./skills/codex-multi-agents/examples/TODO.md -file -status -task-list

Return codes:
  0 success
  1 argument error
  2 file error
  3 data error
  4 lock error
  5 internal error
USAGE
}

parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -dispatch)
        OP_DISPATCH=1
        shift
        ;;
      -done)
        OP_DONE=1
        shift
        ;;
      -pause)
        OP_PAUSE=1
        shift
        ;;
      -continue)
        OP_CONTINUE=1
        shift
        ;;
      -reassign)
        OP_REASSIGN=1
        shift
        ;;
      -new)
        OP_NEW=1
        shift
        ;;
      -status)
        OP_STATUS=1
        shift
        ;;
      -file=*)
        FILE="${1#*=}"
        HAS_FILE=1
        shift
        ;;
      -file)
        if [[ $# -ge 2 && "${2-}" != -* ]]; then
          FILE="$2"
          HAS_FILE=1
          shift 2
        else
          [[ "$HAS_FILE" -eq 1 ]] || err "$RC_ARG" "missing value for -file"
          shift
        fi
        ;;
      -agents-list=*)
        AGENTS_LIST="${1#*=}"
        HAS_AGENTS_LIST=1
        shift
        ;;
      -agents-list)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -agents-list"
        AGENTS_LIST="$2"
        HAS_AGENTS_LIST=1
        shift 2
        ;;
      -task_id=*)
        TASK_ID="${1#*=}"
        HAS_TASK_ID=1
        shift
        ;;
      -task_id)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -task_id"
        TASK_ID="$2"
        HAS_TASK_ID=1
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
      -from=*)
        FROM="${1#*=}"
        HAS_FROM=1
        shift
        ;;
      -from)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -from"
        FROM="$2"
        HAS_FROM=1
        shift 2
        ;;
      -info=*)
        INFO="${1#*=}"
        HAS_INFO=1
        shift
        ;;
      -info)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -info"
        INFO="$2"
        HAS_INFO=1
        shift 2
        ;;
      -worktree=*)
        WORKTREE="${1#*=}"
        HAS_WORKTREE=1
        shift
        ;;
      -worktree)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -worktree"
        WORKTREE="$2"
        HAS_WORKTREE=1
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
      -doing)
        HAS_DOING=1
        shift
        ;;
      -task-list)
        HAS_TASK_LIST=1
        shift
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
      -h|--help)
        usage
        exit "$RC_OK"
        ;;
      *)
        if [[ "$HAS_FILE" -eq 0 && "$1" != -* ]]; then
          FILE="$1"
          HAS_FILE=1
          shift
        else
          err "$RC_ARG" "unknown argument: $1"
        fi
        ;;
    esac
  done

  [[ "$HAS_FILE" -eq 1 ]] || err "$RC_ARG" "missing required argument: -file"
  [[ -n "$(trim "$FILE")" ]] || err "$RC_ARG" "empty value for -file"

  local op_count=$((OP_DISPATCH + OP_DONE + OP_PAUSE + OP_CONTINUE + OP_REASSIGN + OP_NEW + OP_STATUS))
  [[ "$op_count" -eq 1 ]] || err "$RC_ARG" "exactly one operation is required: -dispatch|-done|-pause|-continue|-reassign|-new|-status"

  if [[ "$OP_DISPATCH" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-dispatch requires -task_id"
    [[ "$HAS_TO" -eq 1 ]] || err "$RC_ARG" "-dispatch requires -to"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-dispatch requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    if [[ "$HAS_MESSAGE" -eq 1 ]]; then
      [[ -n "$(trim "$MESSAGE")" ]] || err "$RC_ARG" "empty value for -message"
    fi
    [[ "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 ]] || err "$RC_ARG" "-dispatch does not accept -info/-log/-from/-worktree"
  fi

  if [[ "$OP_DONE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-done requires -task_id"
    [[ "$HAS_LOG" -eq 1 ]] || err "$RC_ARG" "-done requires -log"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-done requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$LOG_FILE")" ]] || err "$RC_ARG" "empty value for -log"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-done does not accept -to/-info/-from/-worktree/-message"
  fi

  if [[ "$OP_PAUSE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-pause requires -task_id"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-pause requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-pause does not accept -to/-info/-log/-from/-worktree/-message"
  fi

  if [[ "$OP_CONTINUE" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-continue requires -task_id"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-continue requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_TO" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-continue does not accept -to/-info/-log/-from/-worktree/-message"
  fi

  if [[ "$OP_REASSIGN" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 1 ]] || err "$RC_ARG" "-reassign requires -task_id"
    [[ "$HAS_TO" -eq 1 ]] || err "$RC_ARG" "-reassign requires -to"
    [[ "$HAS_AGENTS_LIST" -eq 1 ]] || err "$RC_ARG" "-reassign requires -agents-list"
    [[ -n "$(trim "$TASK_ID")" ]] || err "$RC_ARG" "empty value for -task_id"
    [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    [[ -n "$(trim "$AGENTS_LIST")" ]] || err "$RC_ARG" "empty value for -agents-list"
    [[ "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-reassign does not accept -info/-log/-from/-worktree/-message"
  fi

  if [[ "$OP_NEW" -eq 1 ]]; then
    [[ "$HAS_INFO" -eq 1 ]] || err "$RC_ARG" "-new requires -info"
    [[ -n "$(trim "$INFO")" ]] || err "$RC_ARG" "empty value for -info"
    if [[ "$HAS_TO" -eq 1 ]]; then
      [[ -n "$(trim "$TO")" ]] || err "$RC_ARG" "empty value for -to"
    fi
    if [[ "$HAS_FROM" -eq 1 ]]; then
      [[ -n "$(trim "$FROM")" ]] || err "$RC_ARG" "empty value for -from"
    fi
    if [[ "$HAS_WORKTREE" -eq 1 ]]; then
      [[ -n "$(trim "$WORKTREE")" ]] || err "$RC_ARG" "empty value for -worktree"
    fi
    [[ "$HAS_TASK_ID" -eq 0 ]] || err "$RC_ARG" "-new does not accept -task_id"
    [[ "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-new does not accept -message"
  fi

  if [[ "$OP_STATUS" -eq 1 ]]; then
    [[ "$HAS_TASK_ID" -eq 0 && "$HAS_TO" -eq 0 && "$HAS_FROM" -eq 0 && "$HAS_INFO" -eq 0 && "$HAS_LOG" -eq 0 && "$HAS_WORKTREE" -eq 0 && "$HAS_AGENTS_LIST" -eq 0 && "$HAS_MESSAGE" -eq 0 ]] || err "$RC_ARG" "-status does not accept -task_id/-to/-from/-info/-log/-worktree/-agents-list/-message"
    local status_count=$((HAS_DOING + HAS_TASK_LIST))
    [[ "$status_count" -eq 1 ]] || err "$RC_ARG" "-status requires exactly one of -doing/-task-list"
  fi
}

read_config_value() {
  local config_file="$1"
  local key="$2"

  [[ -f "$config_file" ]] || return 1
  python3 - "$config_file" "$key" <<'PY'
import sys

path = sys.argv[1]
key = sys.argv[2]

with open(path, "r", encoding="utf-8") as fh:
    for raw in fh:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        lhs, rhs = line.split("=", 1)
        if lhs.strip() != key:
            continue
        print(rhs.strip())
        break
PY
}

resolve_dispatch_sender() {
  local from_name="${CODEX_MULTI_AGENTS_ROOT_NAME-}"
  if [[ -n "$(trim "$from_name")" ]]; then
    printf "%s" "$from_name"
    return 0
  fi

  from_name="$(read_config_value "${CODEX_MULTI_AGENTS_CONFIG:-$DEFAULT_CONFIG_FILE}" "ROOT_NAME" || true)"
  if [[ -n "$(trim "$from_name")" ]]; then
    printf "%s" "$from_name"
    return 0
  fi

  printf "scheduler"
}

resolve_dispatch_talk_log() {
  local log_path="${CODEX_MULTI_AGENTS_TALK_LOG-}"
  if [[ -n "$(trim "$log_path")" ]]; then
    printf "%s" "$log_path"
    return 0
  fi

  local log_dir=""
  log_dir="$(read_config_value "${CODEX_MULTI_AGENTS_CONFIG:-$DEFAULT_CONFIG_FILE}" "LOG_DIR" || true)"
  if [[ -n "$(trim "$log_dir")" ]]; then
    printf "%s/talk.log" "${log_dir%/}"
    return 0
  fi

  printf "%s/log/talk.log" "$(dirname "$AGENTS_LIST")"
}

send_dispatch_init() {
  if [[ ! -f "$LIST_SCRIPT" ]]; then
    printf "WARN: list script not found, skip dispatch init: %s\n" "$LIST_SCRIPT" >&2
    return 0
  fi

  local output=""
  local rc=0
  output="$(bash "$LIST_SCRIPT" -file "$AGENTS_LIST" -init -name "$TO" 2>&1)" || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    printf "WARN: dispatch init failed for %s: %s\n" "$TO" "$output" >&2
    return 0
  fi

  [[ -z "$output" ]] || printf "%s\n" "$output"
}

should_dispatch_init() {
  return 0
}

send_dispatch_message() {
  [[ "$HAS_MESSAGE" -eq 1 ]] || return 0
  if [[ ! -f "$TMUX_SCRIPT" ]]; then
    printf "ERROR(%s): tmux script not found: %s\n" "$RC_FILE" "$TMUX_SCRIPT" >&2
    return "$RC_FILE"
  fi

  local from_name=""
  local talk_log=""
  local output=""
  local rc=0

  from_name="$(resolve_dispatch_sender)"
  talk_log="$(resolve_dispatch_talk_log)"
  output="$(bash "$TMUX_SCRIPT" -talk -from "$from_name" -to "$TO" -agents-list "$AGENTS_LIST" -message "$MESSAGE" -log "$talk_log" 2>&1)" || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    printf "%s\n" "$output" >&2
    return "$rc"
  fi

  [[ -z "$output" ]] || printf "%s\n" "$output"
}

validate_todo_file() {
  [[ -e "$FILE" ]] || err "$RC_FILE" "file not found: $FILE"
  [[ -f "$FILE" ]] || err "$RC_FILE" "not a regular file: $FILE"
  [[ -r "$FILE" ]] || err "$RC_FILE" "file is not readable: $FILE"
}

acquire_lock_on_file() {
  local path="$1"
  local __fd_var="$2"

  [[ -e "$path" ]] || err "$RC_FILE" "file not found: $path"
  [[ -f "$path" ]] || err "$RC_FILE" "not a regular file: $path"
  [[ -r "$path" ]] || err "$RC_FILE" "file is not readable: $path"

  local fd
  exec {fd}< "$path" || err "$RC_LOCK" "cannot open file for lock: $path"
  flock -x -w 5 "$fd" || err "$RC_LOCK" "cannot acquire lock on file: $path"
  printf -v "$__fd_var" '%s' "$fd"
}

release_lock_fd() {
  local fd="${1-}"
  [[ -n "$fd" ]] || return 0
  eval "exec ${fd}<&-"
}

run_python_core() {
  local op="$1"
  local todo_file="$2"
  local task_id="$3"
  local to="$4"
  local info="$5"
  local log_file="$6"
  local from="$7"
  local worktree="$8"
  local done_file="$9"
  local agents_file="${10}"

  python3 - "$op" "$todo_file" "$task_id" "$to" "$info" "$log_file" "$from" "$worktree" "$done_file" "$agents_file" <<'PY'
import hashlib
import os
import random
import re
import sys
import time
from datetime import datetime

RC_OK = 0
RC_ARG = 1
RC_FILE = 2
RC_DATA = 3
RC_LOCK = 4
RC_INTERNAL = 5

RUN_TABLE_HEADER = ["任务 ID", "发起人", "创建时间", "worktree", "描述", "指派", "状态", "用户指导", "记录文件"]
LIST_TABLE_HEADER = ["任务 ID", "发起人", "创建时间", "worktree", "描述", "指派", "记录文件"]
DONE_TABLE_HEADER = ["任务 ID", "描述", "指派", "完成状态", "完成时间", "日志文件", "备注"]
AGENTS_REQUIRED_COLUMNS = ["姓名", "状态"]


class TaskError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def fail(code: int, message: str) -> None:
    print(f"ERROR({code}): {message}", file=sys.stderr)
    raise TaskError(code, message)


def is_pipe_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def is_sep_row(line: str) -> bool:
    return bool(re.match(r"^\|[\s:\-\|]+\|$", line.strip()))


def split_row(line: str) -> list[str]:
    s = line.strip()
    if not is_pipe_row(s):
        fail(RC_FILE, "invalid table format: non-table row")
    return [c.strip() for c in s[1:-1].split("|")]


def render_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def render_sep(col_count: int) -> str:
    return "| " + " | ".join(["---"] * col_count) + " |"


def read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        fail(RC_FILE, f"file not found: {path}")
    except PermissionError:
        fail(RC_FILE, f"file is not readable: {path}")
    except OSError as exc:
        fail(RC_FILE, f"failed to read file: {path} ({exc})")


def write_atomic(path: str, lines: list[str]) -> None:
    tmp_path = f"{path}.tmp.{os.getpid()}.{random.randint(1000, 9999)}"
    content = "\n".join(lines) + "\n"
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except OSError as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        fail(RC_INTERNAL, f"failed to update file: {path} ({exc})")


def find_section_index(lines: list[str], title: str) -> int:
    for i, line in enumerate(lines):
        if line.strip() == title:
            return i
    fail(RC_FILE, f"invalid table format: section not found: {title}")


def next_h2_index(lines: list[str], start: int) -> int:
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            return i
    return len(lines)


def parse_table_in_section(lines: list[str], section_title: str, expected_header: list[str]) -> dict:
    sec_idx = find_section_index(lines, section_title)
    sec_end = next_h2_index(lines, sec_idx + 1)

    header_idx = -1
    sep_idx = -1
    for i in range(sec_idx + 1, max(sec_end - 1, sec_idx + 1)):
        if is_pipe_row(lines[i]) and is_sep_row(lines[i + 1]):
            header_idx = i
            sep_idx = i + 1
            break

    if header_idx < 0 or sep_idx < 0:
        fail(RC_FILE, f"invalid table format: table not found in section: {section_title}")

    header = split_row(lines[header_idx])
    if header != expected_header:
        fail(
            RC_FILE,
            f"invalid table format: unexpected header in section {section_title}, expect {expected_header}",
        )

    rows: list[list[str]] = []
    data_end = sep_idx
    i = sep_idx + 1
    while i < sec_end and is_pipe_row(lines[i]):
        row = split_row(lines[i])
        if len(row) != len(expected_header):
            fail(RC_FILE, f"invalid table format: row column count mismatch in section {section_title}")
        rows.append(row)
        data_end = i
        i += 1

    return {
        "section_title": section_title,
        "header_idx": header_idx,
        "sep_idx": sep_idx,
        "data_end": data_end,
        "header": header,
        "rows": rows,
    }


def replace_table(lines: list[str], table: dict, new_rows: list[list[str]], keep_original_head: bool = True) -> list[str]:
    if keep_original_head:
        header_line = lines[table["header_idx"]]
        sep_line = lines[table["sep_idx"]]
    else:
        header_line = render_row(table["header"])
        sep_line = render_sep(len(table["header"]))

    block = [header_line, sep_line] + [render_row(r) for r in new_rows]
    return lines[: table["header_idx"]] + block + lines[table["data_end"] + 1 :]


def is_empty_row(cells: list[str]) -> bool:
    return all((c.strip() == "" for c in cells))


def validate_unique_task_ids(exec_rows: list[list[str]], list_rows: list[list[str]]) -> None:
    seen: set[str] = set()
    for row in exec_rows + list_rows:
        if is_empty_row(row):
            continue
        task_id = row[0].strip()
        if not task_id:
            fail(RC_FILE, "invalid table format: empty task id")
        if task_id in seen:
            fail(RC_DATA, f"duplicate task id found: {task_id}")
        seen.add(task_id)


def find_row_index(rows: list[list[str]], task_id: str) -> int:
    for idx, row in enumerate(rows):
        if row[0].strip() == task_id:
            return idx
    return -1


def parse_done_table(done_file: str) -> tuple[list[str], dict]:
    lines = read_lines(done_file)

    if len(lines) == 0 or all((x.strip() == "" for x in lines)):
        lines = [
            "## 已完成任务",
            "",
            render_row(DONE_TABLE_HEADER),
            render_sep(len(DONE_TABLE_HEADER)),
        ]

    for i in range(0, max(len(lines) - 1, 0)):
        if i + 1 >= len(lines):
            break
        if not (is_pipe_row(lines[i]) and is_sep_row(lines[i + 1])):
            continue
        header = split_row(lines[i])
        if header != DONE_TABLE_HEADER:
            continue

        rows: list[list[str]] = []
        data_end = i + 1
        j = i + 2
        while j < len(lines) and is_pipe_row(lines[j]):
            row = split_row(lines[j])
            if len(row) != len(DONE_TABLE_HEADER):
                fail(RC_FILE, "invalid done table format: row column count mismatch")
            rows.append(row)
            data_end = j
            j += 1
        return lines, {
            "header_idx": i,
            "sep_idx": i + 1,
            "data_end": data_end,
            "header": DONE_TABLE_HEADER,
            "rows": rows,
        }

    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.extend([
        "## 已完成任务",
        "",
        render_row(DONE_TABLE_HEADER),
        render_sep(len(DONE_TABLE_HEADER)),
    ])

    header_idx = len(lines) - 2
    sep_idx = len(lines) - 1
    return lines, {
        "header_idx": header_idx,
        "sep_idx": sep_idx,
        "data_end": sep_idx,
        "header": DONE_TABLE_HEADER,
        "rows": [],
    }


def parse_agents_table(agents_file: str) -> tuple[list[str], dict]:
    lines = read_lines(agents_file)

    for i in range(0, max(len(lines) - 1, 0)):
        if i + 1 >= len(lines):
            break
        if not (is_pipe_row(lines[i]) and is_sep_row(lines[i + 1])):
            continue
        header = split_row(lines[i])
        if not all((col in header for col in AGENTS_REQUIRED_COLUMNS)):
            continue

        rows: list[list[str]] = []
        data_end = i + 1
        j = i + 2
        while j < len(lines) and is_pipe_row(lines[j]):
            row = split_row(lines[j])
            if len(row) != len(header):
                fail(RC_FILE, "invalid agents table format: row column count mismatch")
            rows.append(row)
            data_end = j
            j += 1

        return lines, {
            "header_idx": i,
            "sep_idx": i + 1,
            "data_end": data_end,
            "header": header,
            "rows": rows,
            "name_idx": header.index("姓名"),
            "status_idx": header.index("状态"),
        }

    fail(RC_FILE, f"invalid agents table format: required columns not found in {agents_file}")


def find_agent_row_index(rows: list[list[str]], name_idx: int, name: str) -> int:
    for idx, row in enumerate(rows):
        if row[name_idx].strip() == name:
            return idx
    return -1


def count_doing_tasks(exec_rows: list[list[str]], assignee: str) -> int:
    count = 0
    for row in exec_rows:
        if row[5].strip() == assignee and row[6].strip() == "进行中":
            count += 1
    return count


def generate_task_id(info: str, to: str, existing_ids: set[str]) -> str:
    date_part = datetime.now().strftime("%Y%m%d")
    for _ in range(256):
        seed = f"{date_part}|{info}|{to}|{time.time_ns()}|{random.random()}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
        task_id = f"T-{date_part}-{digest}"
        if task_id not in existing_ids:
            return task_id
    fail(RC_INTERNAL, "failed to generate unique task id")


def main() -> int:
    op = sys.argv[1]
    todo_file = sys.argv[2]
    task_id = sys.argv[3]
    to = sys.argv[4]
    info = sys.argv[5]
    log_file = sys.argv[6]
    from_user = sys.argv[7]
    worktree = sys.argv[8]
    done_file = sys.argv[9]
    agents_file = sys.argv[10]

    todo_lines = read_lines(todo_file)
    exec_table = parse_table_in_section(todo_lines, "## 正在执行的任务", RUN_TABLE_HEADER)
    list_table = parse_table_in_section(todo_lines, "## 任务列表", LIST_TABLE_HEADER)

    exec_rows = [r[:] for r in exec_table["rows"]]
    list_rows = [r[:] for r in list_table["rows"]]
    validate_unique_task_ids(exec_rows, list_rows)

    done_lines = None
    done_table = None
    agents_lines = None
    agents_table = None
    agents_rows = None
    message_lines: list[str] = []

    if op in {"dispatch", "done", "pause", "continue", "reassign"}:
        agents_lines, agents_table = parse_agents_table(agents_file)
        agents_rows = [r[:] for r in agents_table["rows"]]

    if op == "status-doing":
        print(render_row(exec_table["header"]))
        print(render_sep(len(exec_table["header"])))
        for row in exec_rows:
            print(render_row(row))
        return RC_OK

    if op == "status-task-list":
        print(render_row(list_table["header"]))
        print(render_sep(len(list_table["header"])))
        for row in list_rows:
            print(render_row(row))
        return RC_OK

    if op == "dispatch":
        if find_row_index(exec_rows, task_id) >= 0:
            fail(RC_DATA, f"task already exists in running list: {task_id}")
        idx = find_row_index(list_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in task list: {task_id}")
        assert agents_table is not None
        assert agents_rows is not None
        agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], to)
        if agent_idx < 0:
            fail(RC_DATA, f"agent not found in agents list: {to}")

        row = list_rows.pop(idx)
        from_val = row[1]
        created_at = row[2]
        worktree_val = row[3]
        desc = row[4]
        record_file = row[6]
        exec_rows.append([row[0], from_val, created_at, worktree_val, desc, to, "进行中", "", record_file])
        agents_rows[agent_idx][agents_table["status_idx"]] = "busy"
        message_lines.append(f"OK: dispatch {task_id} -> {to}")
        message_lines.append(f"OK: replace {to} 状态")

    elif op == "done":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        row = exec_rows.pop(idx)
        assignee = row[5].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")
        done_lines, done_table = parse_done_table(done_file)
        done_rows = [r[:] for r in done_table["rows"]]
        finished_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        done_rows.append([row[0], row[4], row[5], "已完成", finished_at, log_file, ""])
        done_lines = replace_table(done_lines, done_table, done_rows, keep_original_head=False)
        message_lines.append(f"OK: done {task_id}")
        if assignee:
            if count_doing_tasks(exec_rows, assignee) == 0:
                agents_rows[agent_idx][agents_table["status_idx"]] = "free"
                message_lines.append(f"OK: replace {assignee} 状态")
            else:
                agents_rows[agent_idx][agents_table["status_idx"]] = "busy"

    elif op == "pause":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        assignee = exec_rows[idx][5].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")
        exec_rows[idx][6] = "暂停"
        message_lines.append(f"OK: pause {task_id}")
        if assignee:
            if count_doing_tasks(exec_rows, assignee) == 0:
                agents_rows[agent_idx][agents_table["status_idx"]] = "free"
                message_lines.append(f"OK: replace {assignee} 状态")
            else:
                agents_rows[agent_idx][agents_table["status_idx"]] = "busy"

    elif op == "continue":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        if exec_rows[idx][6].strip() != "暂停":
            fail(RC_DATA, f"task status is not paused: {task_id}")

        assignee = exec_rows[idx][5].strip()
        if assignee:
            assert agents_table is not None
            assert agents_rows is not None
            agent_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], assignee)
            if agent_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {assignee}")

        exec_rows[idx][6] = "进行中"
        message_lines.append(f"OK: continue {task_id}")
        if assignee:
            agents_rows[agent_idx][agents_table["status_idx"]] = "busy"
            message_lines.append(f"OK: replace {assignee} 状态")

    elif op == "reassign":
        idx = find_row_index(exec_rows, task_id)
        if idx < 0:
            fail(RC_DATA, f"task not found in running list: {task_id}")

        assert agents_table is not None
        assert agents_rows is not None
        new_assignee = to.strip()
        if not new_assignee:
            fail(RC_ARG, "empty value for -to")
        new_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], new_assignee)
        if new_idx < 0:
            fail(RC_DATA, f"agent not found in agents list: {new_assignee}")

        old_assignee = exec_rows[idx][5].strip()
        old_idx = None
        if old_assignee:
            old_idx = find_agent_row_index(agents_rows, agents_table["name_idx"], old_assignee)
            if old_idx < 0:
                fail(RC_DATA, f"agent not found in agents list: {old_assignee}")

        exec_rows[idx][5] = new_assignee
        message_lines.append(f"OK: reassign {task_id} -> {new_assignee}")

        updated: set[str] = set()

        def update_agent(name: str, row_idx: int | None) -> None:
            if not name or row_idx is None or name in updated:
                return
            status = "busy" if count_doing_tasks(exec_rows, name) > 0 else "free"
            agents_rows[row_idx][agents_table["status_idx"]] = status
            message_lines.append(f"OK: replace {name} 状态")
            updated.add(name)

        update_agent(old_assignee, old_idx)
        update_agent(new_assignee, new_idx)

    elif op == "new":
        existing_ids = {r[0].strip() for r in (exec_rows + list_rows) if not is_empty_row(r)}
        new_id = generate_task_id(info, to, existing_ids)
        created_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        from_val = from_user or ""
        worktree_val = worktree or ""
        record_file = log_file or ""
        list_rows.append([new_id, from_val, created_at, worktree_val, info, to, record_file])
        message_lines.append(f"OK: new {new_id}")

    else:
        fail(RC_INTERNAL, f"unsupported operation: {op}")

    # 先写 DONE，再写 TODO。失败时至少保留可追踪记录。
    if done_lines is not None:
        write_atomic(done_file, done_lines)

    if agents_lines is not None and agents_table is not None and agents_rows is not None:
        agents_lines = replace_table(agents_lines, agents_table, agents_rows, keep_original_head=True)
        write_atomic(agents_file, agents_lines)

    tables = [
        (exec_table, exec_rows),
        (list_table, list_rows),
    ]
    updated = todo_lines[:]
    for table, rows in sorted(tables, key=lambda x: x[0]["header_idx"], reverse=True):
        updated = replace_table(updated, table, rows, keep_original_head=True)

    write_atomic(todo_file, updated)
    for line in message_lines:
        print(line)
    return RC_OK


if __name__ == "__main__":
    try:
        rc = main()
    except TaskError as exc:
        sys.exit(exc.code)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR({RC_INTERNAL}): internal error: {exc}", file=sys.stderr)
        sys.exit(RC_INTERNAL)
    else:
        sys.exit(rc)
PY
}

main() {
  parse_args "$@"
  validate_todo_file

  local op=""
  local done_file=""
  local done_lock_fd=""
  local agents_lock_fd=""

  if [[ "$OP_DISPATCH" -eq 1 ]]; then
    op="dispatch"
  elif [[ "$OP_DONE" -eq 1 ]]; then
    op="done"
  elif [[ "$OP_PAUSE" -eq 1 ]]; then
    op="pause"
  elif [[ "$OP_CONTINUE" -eq 1 ]]; then
    op="continue"
  elif [[ "$OP_REASSIGN" -eq 1 ]]; then
    op="reassign"
  elif [[ "$OP_NEW" -eq 1 ]]; then
    op="new"
  elif [[ "$OP_STATUS" -eq 1 ]]; then
    if [[ "$HAS_DOING" -eq 1 ]]; then
      op="status-doing"
    else
      op="status-task-list"
    fi
  else
    err "$RC_INTERNAL" "unexpected operation state"
  fi

  if [[ "$op" == "status-doing" || "$op" == "status-task-list" ]]; then
    run_python_core "$op" "$FILE" "" "" "" "" "" "" "" ""
    exit "$RC_OK"
  fi

  local todo_lock_fd=""
  acquire_lock_on_file "$FILE" todo_lock_fd

  if [[ "$op" == "done" ]]; then
    done_file="$(dirname "$FILE")/DONE.md"
    if [[ ! -e "$done_file" ]]; then
      : > "$done_file" || err "$RC_FILE" "failed to create done file: $done_file"
    fi
    acquire_lock_on_file "$done_file" done_lock_fd
  fi

  if [[ "$op" == "dispatch" || "$op" == "done" || "$op" == "pause" || "$op" == "continue" || "$op" == "reassign" ]]; then
    acquire_lock_on_file "$AGENTS_LIST" agents_lock_fd
  fi

  if [[ "$op" == "dispatch" ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
    if should_dispatch_init; then
      send_dispatch_init
    fi
    acquire_lock_on_file "$FILE" todo_lock_fd
    acquire_lock_on_file "$AGENTS_LIST" agents_lock_fd
  fi

  run_python_core "$op" "$FILE" "$TASK_ID" "$TO" "$INFO" "$LOG_FILE" "$FROM" "$WORKTREE" "$done_file" "$AGENTS_LIST"
  local rc=$?
  if [[ "$rc" -ne 0 ]]; then
    exit "$rc"
  fi

  if [[ "$op" == "dispatch" && "$HAS_MESSAGE" -eq 1 ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
    send_dispatch_message
    local talk_rc=$?
    if [[ "$talk_rc" -ne 0 ]]; then
      printf "ERROR(%s): dispatch succeeded but message delivery failed for task %s; retry codex-multi-agents-tmux.sh -talk only\n" "$talk_rc" "$TASK_ID" >&2
      exit "$talk_rc"
    fi
  elif [[ "$op" == "dispatch" ]]; then
    release_lock_fd "$agents_lock_fd"
    release_lock_fd "$todo_lock_fd"
  fi
}

main "$@"
