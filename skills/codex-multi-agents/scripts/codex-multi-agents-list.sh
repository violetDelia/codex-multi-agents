#!/usr/bin/env bash
# codex-multi-agents-list.sh
#
# 创建者: 榕
# 最后一次更改: 榕
#
# 功能:
# - 读取/维护 agents 名单（Markdown 表格）。
# - 支持 status、find、replace、add、delete、init、compact 七类操作。
# - 约束姓名唯一、姓名字段不可修改、写操作加锁。
#
# 对应文件:
# - spec: /home/lfr/kernelcode_generate/spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# - test: /home/lfr/kernelcode_generate/test/codex-multi-agents/test_codex-multi-agents-list.py
# - impl: /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
#
# 使用示例:
# - 读取:  codex-multi-agents-list.sh -file ./agents-lists.md -status
# - 查询:  codex-multi-agents-list.sh -file ./agents-lists.md -find -name 小明 -key 归档文件
# - 新增:  codex-multi-agents-list.sh -file ./agents-lists.md -add -name 小明 -type codex
# - 修改:  codex-multi-agents-list.sh -file ./agents-lists.md -replace -name 小明 -key 状态 -value ready
# - 删除:  codex-multi-agents-list.sh -file ./agents-lists.md -delete -name 小明
# - 初始化: codex-multi-agents-list.sh -file ./agents-lists.md -init -name 小明
# - 压缩:  codex-multi-agents-list.sh -file ./agents-lists.md -compact -name 小明
# - 等价写法: codex-multi-agents-list.sh -file=./agents-lists.md -add -name=小明 -type=codex

set -u
set -o pipefail
shopt -s extglob

readonly RC_OK=0
readonly RC_ARG=1
readonly RC_FILE=2
readonly RC_DATA=3
readonly RC_LOCK=4
readonly RC_INTERNAL=5
readonly REQUIRED_COLUMNS=("姓名" "状态" "会话" "agent session" "介绍" "提示词" "归档文件")
readonly STARTUP_COLUMNS=("启动设置" "启动类型")

FILE=""
OP_STATUS=0
OP_FIND=0
OP_REPLACE=0
OP_ADD=0
OP_DELETE=0
OP_INIT=0
OP_COMPACT=0
NAME=""
KEY=""
VALUE=""
TYPE=""
HAS_FILE=0
HAS_NAME=0
HAS_KEY=0
HAS_VALUE=0
HAS_TYPE=0

table_header_idx=-1
table_sep_idx=-1
table_data_start_idx=-1
table_data_end_idx=-1
col_count=0
name_col_idx=-1
session_col_idx=-1
agent_session_col_idx=-1
worktree_col_idx=-1
startup_col_idx=-1
prompt_col_idx=-1
archive_col_idx=-1
key_col_idx=-1
duty_col_idx=-1
declare -a file_lines=()
declare -a header_cells=()
declare -a data_rows=()
declare -a data_rows_idx=()
declare -a col_max_widths=()
found_row_idx=-1

# 去除字符串首尾空白。
trim() {
  local s="${1-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

# 统一错误输出并按约定错误码退出。
err() {
  local code="$1"
  shift
  printf "ERROR(%s): %s\n" "$code" "$*" >&2
  exit "$code"
}

# 判断一行是否为 Markdown 管道表格行。
is_pipe_row() {
  local line="$1"
  [[ "$line" =~ ^[[:space:]]*\|.*\|[[:space:]]*$ ]]
}

# 判断一行是否为 Markdown 表头分隔行（---）。
is_sep_row() {
  local line="$1"
  [[ "$line" =~ ^[[:space:]]*\|[[:space:]:-][[:space:]:|\-]*\|[[:space:]]*$ ]]
}

# 拆分 Markdown 行为单元格数组，并做 trim。
split_row() {
  local line="$1"
  local -n out_ref="$2"
  local core
  core="$(trim "$line")"
  core="${core#|}"
  core="${core%|}"

  local raw=()
  IFS='|' read -r -a raw <<< "$core"
  out_ref=()

  local i cell
  for i in "${!raw[@]}"; do
    cell="$(trim "${raw[$i]}")"
    out_ref+=("$cell")
  done
}

# 将单元格数组渲染为标准 Markdown 行。
render_row() {
  local -n arr_ref="$1"
  local out="|"
  local i
  for i in "${!arr_ref[@]}"; do
    out+=" ${arr_ref[$i]} |"
  done
  printf "%s" "$out"
}

# 打印帮助信息和返回码约定。
usage() {
  cat <<'EOF'
Usage:
  codex-multi-agents-list.sh -file <path> -status
  codex-multi-agents-list.sh -file <path> -find -name <name> -key <field>
  codex-multi-agents-list.sh -file <path> -replace -name <name> -key <field> -value <value>
  codex-multi-agents-list.sh -file <path> -add -name <name> -type <startup_type>
  codex-multi-agents-list.sh -file <path> -delete -name <name>
  codex-multi-agents-list.sh -file <path> -init -name <name>
  codex-multi-agents-list.sh -file <path> -compact -name <name>

Examples:
  codex-multi-agents-list.sh -file ./agents-lists.md -status
  codex-multi-agents-list.sh -file ./agents-lists.md -find -name 小明 -key 归档文件
  codex-multi-agents-list.sh -file=./agents-lists.md -add -name=小明 -type=codex
  codex-multi-agents-list.sh -file ./agents-lists.md -replace -name 小明 -key 状态 -value ready
  codex-multi-agents-list.sh -file ./agents-lists.md -delete -name 小明
  codex-multi-agents-list.sh -file ./agents-lists.md -init -name 小明
  codex-multi-agents-list.sh -file ./agents-lists.md -compact -name 小明

Return codes:
  0 success
  1 argument error
  2 file error
  3 data error
  4 lock error
  5 internal error
EOF
}

# 解析命令行参数，支持 "空格" 与 "key=value" 两种写法。
parse_args() {
  if [[ $# -eq 0 ]]; then
    usage
    err "$RC_ARG" "missing arguments"
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -file=*)
        FILE="${1#*=}"
        HAS_FILE=1
        shift
        ;;
      -file)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -file"
        FILE="$2"
        HAS_FILE=1
        shift 2
        ;;
      -status)
        OP_STATUS=1
        shift
        ;;
      -find)
        OP_FIND=1
        shift
        ;;
      -replace)
        OP_REPLACE=1
        shift
        ;;
      -add)
        OP_ADD=1
        shift
        ;;
      -delete)
        OP_DELETE=1
        shift
        ;;
      -init)
        OP_INIT=1
        shift
        ;;
      -compact)
        OP_COMPACT=1
        shift
        ;;
      -name=*)
        NAME="${1#*=}"
        HAS_NAME=1
        shift
        ;;
      -name)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -name"
        NAME="$2"
        HAS_NAME=1
        shift 2
        ;;
      -key=*)
        KEY="${1#*=}"
        HAS_KEY=1
        shift
        ;;
      -key)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -key"
        KEY="$2"
        HAS_KEY=1
        shift 2
        ;;
      -value=*)
        VALUE="${1#*=}"
        HAS_VALUE=1
        shift
        ;;
      -value)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -value"
        VALUE="$2"
        HAS_VALUE=1
        shift 2
        ;;
      -type=*)
        TYPE="${1#*=}"
        HAS_TYPE=1
        shift
        ;;
      -type)
        [[ $# -ge 2 ]] || err "$RC_ARG" "missing value for -type"
        TYPE="$2"
        HAS_TYPE=1
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

  [[ "$HAS_FILE" -eq 1 ]] || err "$RC_ARG" "missing required argument: -file"
  [[ -n "$FILE" ]] || err "$RC_ARG" "empty value for -file"

  local op_count=$((OP_STATUS + OP_FIND + OP_REPLACE + OP_ADD + OP_DELETE + OP_INIT + OP_COMPACT))
  [[ "$op_count" -eq 1 ]] || err "$RC_ARG" "exactly one operation is required: -status|-find|-replace|-add|-delete|-init|-compact"

  if [[ "$OP_STATUS" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 0 && "$HAS_KEY" -eq 0 && "$HAS_VALUE" -eq 0 && "$HAS_TYPE" -eq 0 ]] || err "$RC_ARG" "-status does not accept -name/-key/-value/-type"
  fi

  if [[ "$OP_FIND" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "-find requires -name"
    [[ "$HAS_KEY" -eq 1 ]] || err "$RC_ARG" "-find requires -key"
    [[ -n "$NAME" ]] || err "$RC_ARG" "empty value for -name"
    [[ -n "$KEY" ]] || err "$RC_ARG" "empty value for -key"
    [[ "$HAS_VALUE" -eq 0 && "$HAS_TYPE" -eq 0 ]] || err "$RC_ARG" "-find does not accept -value/-type"
  fi

  if [[ "$OP_REPLACE" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "-replace requires -name"
    [[ "$HAS_KEY" -eq 1 ]] || err "$RC_ARG" "-replace requires -key"
    [[ "$HAS_VALUE" -eq 1 ]] || err "$RC_ARG" "-replace requires -value"
    [[ -n "$NAME" ]] || err "$RC_ARG" "empty value for -name"
    [[ -n "$KEY" ]] || err "$RC_ARG" "empty value for -key"
    [[ "$HAS_TYPE" -eq 0 ]] || err "$RC_ARG" "-replace does not accept -type"
  fi

  if [[ "$OP_ADD" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "operation requires -name"
    [[ -n "$NAME" ]] || err "$RC_ARG" "empty value for -name"
    [[ "$HAS_TYPE" -eq 1 ]] || err "$RC_ARG" "-add requires -type"
    [[ -n "$TYPE" ]] || err "$RC_ARG" "empty value for -type"
    [[ "$HAS_KEY" -eq 0 && "$HAS_VALUE" -eq 0 ]] || err "$RC_ARG" "-add does not accept -key/-value"
  fi

  if [[ "$OP_DELETE" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "operation requires -name"
    [[ -n "$NAME" ]] || err "$RC_ARG" "empty value for -name"
    [[ "$HAS_KEY" -eq 0 && "$HAS_VALUE" -eq 0 && "$HAS_TYPE" -eq 0 ]] || err "$RC_ARG" "-delete does not accept -key/-value/-type"
  fi

  if [[ "$OP_INIT" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "-init requires -name"
    [[ -n "$NAME" ]] || err "$RC_ARG" "empty value for -name"
    [[ "$HAS_KEY" -eq 0 && "$HAS_VALUE" -eq 0 && "$HAS_TYPE" -eq 0 ]] || err "$RC_ARG" "-init does not accept -key/-value/-type"
  fi

  if [[ "$OP_COMPACT" -eq 1 ]]; then
    [[ "$HAS_NAME" -eq 1 ]] || err "$RC_ARG" "-compact requires -name"
    [[ -n "$NAME" ]] || err "$RC_ARG" "empty value for -name"
    [[ "$HAS_KEY" -eq 0 && "$HAS_VALUE" -eq 0 && "$HAS_TYPE" -eq 0 ]] || err "$RC_ARG" "-compact does not accept -key/-value/-type"
  fi
}

# 读取目标文件并完成基础可读性校验。
load_file() {
  [[ -e "$FILE" ]] || err "$RC_FILE" "file not found: $FILE"
  [[ -f "$FILE" ]] || err "$RC_FILE" "not a regular file: $FILE"
  [[ -r "$FILE" ]] || err "$RC_FILE" "file is not readable: $FILE"

  if ! mapfile -t file_lines < "$FILE"; then
    err "$RC_FILE" "failed to read file: $FILE"
  fi
}

# 解析 Markdown 表格结构，定位表头/分隔/数据区并缓存关键索引。
parse_table() {
  local i
  local n="${#file_lines[@]}"

  for ((i=0; i<n; i++)); do
    if is_pipe_row "${file_lines[$i]}"; then
      if (( i + 1 < n )) && is_sep_row "${file_lines[$((i + 1))]}"; then
        table_header_idx="$i"
        table_sep_idx="$((i + 1))"
        break
      fi
    fi
  done

  (( table_header_idx >= 0 )) || err "$RC_FILE" "invalid table format: header row not found"
  (( table_sep_idx > table_header_idx )) || err "$RC_FILE" "invalid table format: separator row not found"

  split_row "${file_lines[$table_header_idx]}" header_cells
  col_count="${#header_cells[@]}"
  (( col_count > 0 )) || err "$RC_FILE" "invalid table format: empty header"

  local required_col
  local required_idx
  local found_required
  for required_idx in "${!REQUIRED_COLUMNS[@]}"; do
    required_col="${REQUIRED_COLUMNS[$required_idx]}"
    found_required=0
    for i in "${!header_cells[@]}"; do
      if [[ "${header_cells[$i]}" == "$required_col" ]]; then
        found_required=1
        break
      fi
    done
    (( found_required == 1 )) || err "$RC_FILE" "invalid table format: missing required column '$required_col'"
  done

  name_col_idx=-1
  session_col_idx=-1
  agent_session_col_idx=-1
  worktree_col_idx=-1
  startup_col_idx=-1
  prompt_col_idx=-1
  archive_col_idx=-1
  key_col_idx=-1
  duty_col_idx=-1
  local startup_name
  local startup_name_idx
  local startup_found=0
  for startup_name_idx in "${!STARTUP_COLUMNS[@]}"; do
    startup_name="${STARTUP_COLUMNS[$startup_name_idx]}"
    for i in "${!header_cells[@]}"; do
      if [[ "${header_cells[$i]}" == "$startup_name" ]]; then
        startup_col_idx="$i"
        startup_found=1
        break
      fi
    done
    if (( startup_found == 1 )); then
      break
    fi
  done
  (( startup_found == 1 )) || err "$RC_FILE" "invalid table format: missing required column '启动设置/启动类型'"

  for i in "${!header_cells[@]}"; do
    if [[ "${header_cells[$i]}" == "姓名" ]]; then
      name_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "会话" ]]; then
      session_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "agent session" ]]; then
      agent_session_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "worktree" ]]; then
      worktree_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "提示词" ]]; then
      prompt_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "归档文件" ]]; then
      archive_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "职责" ]]; then
      duty_col_idx="$i"
    fi
    if [[ "${header_cells[$i]}" == "$KEY" ]]; then
      key_col_idx="$i"
    fi
  done
  (( name_col_idx >= 0 )) || err "$RC_FILE" "invalid table format: missing required column '姓名'"

  data_rows=()
  data_rows_idx=()
  table_data_start_idx=$((table_sep_idx + 1))
  table_data_end_idx="$table_sep_idx"

  for ((i=table_data_start_idx; i<n; i++)); do
    if is_pipe_row "${file_lines[$i]}"; then
      data_rows+=("${file_lines[$i]}")
      data_rows_idx+=("$i")
      table_data_end_idx="$i"
    else
      break
    fi
  done

  rebuild_col_max_widths
}

# 统计各列最大显示宽度（含中文宽字符），用于 status 对齐输出。
rebuild_col_max_widths() {
  local -a width_rows=()
  local row

  width_rows+=("${file_lines[$table_header_idx]}")
  for row in "${data_rows[@]}"; do
    width_rows+=("$row")
  done

  if [[ "${#width_rows[@]}" -eq 0 ]]; then
    col_max_widths=()
    return
  fi

  if ! mapfile -t col_max_widths < <(python3 - "$col_count" "${width_rows[@]}" <<'PY'
import sys
import unicodedata


def split_row(line: str):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def display_width(text: str) -> int:
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


col_count = int(sys.argv[1])
rows = sys.argv[2:]
max_widths = [0] * col_count

for row in rows:
    if not row.strip():
        continue
    cells = split_row(row)
    if len(cells) < col_count:
        cells.extend([""] * (col_count - len(cells)))
    elif len(cells) > col_count:
        cells = cells[:col_count]
    for i, cell in enumerate(cells):
        w = display_width(cell)
        if w > max_widths[i]:
            max_widths[i] = w

for w in max_widths:
    print(w)
PY
  ); then
    err "$RC_INTERNAL" "failed to compute max column widths"
  fi
}

# 校验数据行完整性与姓名唯一性。
validate_data_rows() {
  local row_idx
  local -a cells=()
  local -A seen=()
  local name
  local cell_len
  local pad_idx

  for row_idx in "${!data_rows[@]}"; do
    split_row "${data_rows[$row_idx]}" cells
    cell_len="${#cells[@]}"
    if (( cell_len > col_count )); then
      err "$RC_FILE" "invalid table format: row column count mismatch at line $((data_rows_idx[row_idx] + 1))"
    fi
    if (( cell_len < col_count )); then
      # 兼容新增列场景：历史行缺少尾部列时自动补空值。
      for ((pad_idx=cell_len; pad_idx<col_count; pad_idx++)); do
        cells+=("")
      done
      data_rows[$row_idx]="$(render_row cells)"
    fi

    name="${cells[$name_col_idx]}"
    [[ -n "$name" ]] || continue
    if [[ -n "${seen[$name]+x}" ]]; then
      err "$RC_DATA" "duplicate 姓名 found: $name"
    fi
    seen["$name"]=1
  done
}

# 将更新后的数据行原子写回文件（临时文件 + mv）。
write_updated_file() {
  local -n new_rows_ref="$1"
  local tmp_file
  tmp_file="$(mktemp "${FILE}.tmp.XXXXXX")" || err "$RC_INTERNAL" "failed to create temp file"

  local i
  {
    for ((i=0; i<=table_sep_idx; i++)); do
      printf "%s\n" "${file_lines[$i]}"
    done

    for i in "${!new_rows_ref[@]}"; do
      printf "%s\n" "${new_rows_ref[$i]}"
    done

    for ((i=table_data_end_idx + 1; i<${#file_lines[@]}; i++)); do
      printf "%s\n" "${file_lines[$i]}"
    done
  } > "$tmp_file" || {
    rm -f "$tmp_file"
    err "$RC_INTERNAL" "failed to write temp file"
  }

  mv "$tmp_file" "$FILE" || {
    rm -f "$tmp_file"
    err "$RC_INTERNAL" "failed to update file: $FILE"
  }
}

# 按姓名定位唯一数据行索引；不存在或重复均报错。
find_row_by_name() {
  local target="$1"
  local idx
  local -a cells=()
  local found=-1
  local count=0

  for idx in "${!data_rows[@]}"; do
    split_row "${data_rows[$idx]}" cells
    if [[ "${cells[$name_col_idx]}" == "$target" ]]; then
      found="$idx"
      count=$((count + 1))
    fi
  done

  if [[ "$count" -eq 0 ]]; then
    err "$RC_DATA" "agent not found: $target"
  fi
  if [[ "$count" -gt 1 ]]; then
    err "$RC_DATA" "agent name is not unique: $target"
  fi

  found_row_idx="$found"
}

# 判断一行是否包含任意非空字段。
row_has_content() {
  local row="$1"
  local -a cells=()
  split_row "$row" cells

  local cell
  for cell in "${cells[@]}"; do
    if [[ -n "$(trim "$cell")" ]]; then
      return 0
    fi
  done
  return 1
}

# 按列宽输出对齐后的 Markdown 表格（适配中文显示宽度）。
print_pretty_table() {
  local -n rows_ref="$1"
  local widths_csv
  widths_csv="$(IFS=,; echo "${col_max_widths[*]}")"

  python3 - "$widths_csv" "${rows_ref[@]}" <<'PY' || err "$RC_INTERNAL" "failed to format status output"
import sys
import unicodedata


def split_row(line: str):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def display_width(text: str) -> int:
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def pad_right(text: str, width: int) -> str:
    pad = width - display_width(text)
    if pad < 0:
        pad = 0
    return text + (" " * pad)


widths_arg = sys.argv[1] if len(sys.argv) > 1 else ""
rows = [split_row(x) for x in sys.argv[2:] if x.strip()]
if not rows:
    sys.exit(0)

cols = max(len(r) for r in rows)
for r in rows:
    if len(r) < cols:
        r.extend([""] * (cols - len(r)))

if widths_arg:
    widths = [int(x) if x else 0 for x in widths_arg.split(",")]
else:
    widths = []

if len(widths) < cols:
    widths.extend([0] * (cols - len(widths)))
elif len(widths) > cols:
    widths = widths[:cols]

# Safety: if visible rows contain wider values, expand widths dynamically.
for r in rows:
    for i, c in enumerate(r):
        w = display_width(c)
        if w > widths[i]:
            widths[i] = w

def print_row(r):
    print("| " + " | ".join(pad_right(c, widths[i]) for i, c in enumerate(r)) + " |")

print_row(rows[0])
print("| " + " | ".join("-" * max(widths[i], 3) for i in range(cols)) + " |")
for r in rows[1:]:
    print_row(r)
PY
}

# status 操作：输出表头和非全空数据行。
do_status() {
  local -a status_rows=()
  local row

  # Always show header; hide fully empty data rows to keep status output compact.
  status_rows+=("${file_lines[$table_header_idx]}")
  for row in "${data_rows[@]}"; do
    if row_has_content "$row"; then
      status_rows+=("$row")
    fi
  done

  print_pretty_table status_rows
}

# find 操作：按姓名读取指定字段值。
do_find() {
  (( key_col_idx >= 0 )) || err "$RC_DATA" "invalid field name: $KEY"
  find_row_by_name "$NAME"
  local target_idx="$found_row_idx"

  local -a cells=()
  split_row "${data_rows[$target_idx]}" cells
  printf "%s\n" "${cells[$key_col_idx]}"
}

# replace 操作：按姓名更新指定字段。
do_replace() {
  [[ "$KEY" != "姓名" ]] || err "$RC_DATA" "field '姓名' is immutable and cannot be modified"
  (( key_col_idx >= 0 )) || err "$RC_DATA" "invalid field name: $KEY"

  find_row_by_name "$NAME"
  local target_idx="$found_row_idx"

  local -a cells=()
  split_row "${data_rows[$target_idx]}" cells
  cells[$key_col_idx]="$VALUE"
  data_rows[$target_idx]="$(render_row cells)"

  write_updated_file data_rows
  printf "OK: replace %s %s\n" "$NAME" "$KEY"
}

# 生成唯一 ASCII 值（不可含中文），避免与现有值重复。
generate_unique_ascii_value() {
  local prefix="$1"
  shift
  local -a existing_values=("$@")
  python3 - "$prefix" "${existing_values[@]}" <<'PY' || return 1
import secrets
import string
import sys

prefix = sys.argv[1]
existing = set(sys.argv[2:])
alphabet = string.ascii_lowercase + string.digits

for _ in range(256):
    token = prefix + "".join(secrets.choice(alphabet) for _ in range(12))
    if token not in existing:
        print(token)
        sys.exit(0)

sys.exit(1)
PY
}

# add 操作：新增一行，写入姓名和启动类型并自动生成唯一会话字段。
do_add() {
  local -a row=()
  local -a cells=()
  local -a existing_sessions=()
  local -a existing_agent_sessions=()
  local -a existing_worktrees=()
  local idx
  local session
  local agent_session
  local worktree

  for idx in "${!data_rows[@]}"; do
    split_row "${data_rows[$idx]}" cells
    if [[ "${cells[$name_col_idx]}" == "$NAME" ]]; then
      err "$RC_DATA" "agent already exists: $NAME"
    fi

    if (( session_col_idx >= 0 )); then
      if [[ -n "${cells[$session_col_idx]}" ]]; then
        existing_sessions+=("${cells[$session_col_idx]}")
      fi
    fi
    if (( agent_session_col_idx >= 0 )); then
      if [[ -n "${cells[$agent_session_col_idx]}" ]]; then
        existing_agent_sessions+=("${cells[$agent_session_col_idx]}")
      fi
    fi
    if (( worktree_col_idx >= 0 )); then
      if [[ -n "${cells[$worktree_col_idx]}" ]]; then
        existing_worktrees+=("${cells[$worktree_col_idx]}")
      fi
    fi
  done

  (( session_col_idx >= 0 )) || err "$RC_DATA" "missing required column for add: 会话"
  (( agent_session_col_idx >= 0 )) || err "$RC_DATA" "missing required column for add: agent session"
  (( startup_col_idx >= 0 )) || err "$RC_DATA" "missing required column for add: 启动设置/启动类型"
  session="$(generate_unique_ascii_value "sess-" "${existing_sessions[@]}")" || err "$RC_INTERNAL" "failed to generate unique session"
  agent_session="$(generate_unique_ascii_value "agent-" "${existing_agent_sessions[@]}")" || err "$RC_INTERNAL" "failed to generate unique agent session"
  [[ -n "$session" ]] || err "$RC_INTERNAL" "failed to generate unique session"
  [[ -n "$agent_session" ]] || err "$RC_INTERNAL" "failed to generate unique agent session"
  if (( worktree_col_idx >= 0 )); then
    worktree="$(generate_unique_ascii_value "wt-" "${existing_worktrees[@]}")" || err "$RC_INTERNAL" "failed to generate unique worktree"
    [[ -n "$worktree" ]] || err "$RC_INTERNAL" "failed to generate unique worktree"
  fi

  for ((idx=0; idx<col_count; idx++)); do
    row+=("")
  done
  row[$name_col_idx]="$NAME"
  row[$session_col_idx]="$session"
  row[$startup_col_idx]="$TYPE"
  row[$agent_session_col_idx]="$agent_session"
  if (( worktree_col_idx >= 0 )); then
    row[$worktree_col_idx]="$worktree"
  fi
  data_rows+=("$(render_row row)")

  write_updated_file data_rows
  printf "OK: add %s\n" "$NAME"
}

# init 操作：读取角色关键信息并向其会话发送初始化消息。
do_init() {
  find_row_by_name "$NAME"
  local target_idx="$found_row_idx"

  local -a cells=()
  split_row "${data_rows[$target_idx]}" cells

  local session prompt_file archive duty worktree
  session="${cells[$session_col_idx]}"
  prompt_file="${cells[$prompt_col_idx]}"
  archive="${cells[$archive_col_idx]}"
  duty=""
  if (( duty_col_idx >= 0 )); then
    duty="${cells[$duty_col_idx]}"
  fi
  worktree=""
  if (( worktree_col_idx >= 0 )); then
    worktree="${cells[$worktree_col_idx]}"
  fi

  [[ -n "$session" ]] || err "$RC_DATA" "empty session for agent: $NAME"
  command -v tmux >/dev/null 2>&1 || err "$RC_FILE" "tmux not found in PATH"
  tmux has-session -t "$session" >/dev/null 2>&1 || err "$RC_DATA" "target session not found: $session"

  local message
  message="你的名字叫做${NAME}，从现在起只需要严格按照${prompt_file}进行工作以及\"AGENTS.md\"进行工作,你的专属文件夹在${archive}，你的职责是${duty}。请仔细阅读${prompt_file}，确保更新信息同步"
  tmux send-keys -t "$session" "$message" || err "$RC_INTERNAL" "failed to send init message to session: $session"
  sleep 1 || err "$RC_INTERNAL" "sleep failed after init message: $session"
  tmux send-keys -t "$session" ENTER || err "$RC_INTERNAL" "failed to confirm init message: $session"
  printf "OK: init %s\n" "$NAME"
}

# compact 操作：压缩上下文并提示回报管理员。
do_compact() {
  find_row_by_name "$NAME"
  local target_idx="$found_row_idx"

  local -a cells=()
  split_row "${data_rows[$target_idx]}" cells

  local session prompt_file archive duty worktree
  session="${cells[$session_col_idx]}"
  prompt_file="${cells[$prompt_col_idx]}"
  archive="${cells[$archive_col_idx]}"
  duty=""
  if (( duty_col_idx >= 0 )); then
    duty="${cells[$duty_col_idx]}"
  fi
  worktree=""
  if (( worktree_col_idx >= 0 )); then
    worktree="${cells[$worktree_col_idx]}"
  fi

  [[ -n "$session" ]] || err "$RC_DATA" "empty session for agent: $NAME"
  command -v tmux >/dev/null 2>&1 || err "$RC_FILE" "tmux not found in PATH"
  tmux has-session -t "$session" >/dev/null 2>&1 || err "$RC_DATA" "target session not found: $session"

  tmux send-keys -t "$session" /compact || err "$RC_INTERNAL" "failed to send compact command to session: $session"
  sleep 1 || err "$RC_INTERNAL" "sleep failed after compact command: $session"
  tmux send-keys -t "$session" ENTER || err "$RC_INTERNAL" "failed to confirm compact command: $session"
  sleep 3 || err "$RC_INTERNAL" "sleep failed before compact report message: $session"

  local message
  message="你的名字叫做${NAME}，从现在起只需要严格按照${prompt_file}进行工作以及\"AGENTS.md\"进行工作，当你压缩完成后，回报管理员。"
  tmux send-keys -t "$session" "$message" || err "$RC_INTERNAL" "failed to send compact report message to session: $session"
  sleep 1 || err "$RC_INTERNAL" "sleep failed after compact report message: $session"
  tmux send-keys -t "$session" ENTER || err "$RC_INTERNAL" "failed to confirm compact report message: $session"
  printf "OK: compact %s\n" "$NAME"
}

# delete 操作：按姓名删除目标行。
do_delete() {
  find_row_by_name "$NAME"
  local target_idx="$found_row_idx"

  local -a new_rows=()
  local idx
  for idx in "${!data_rows[@]}"; do
    if [[ "$idx" != "$target_idx" ]]; then
      new_rows+=("${data_rows[$idx]}")
    fi
  done

  write_updated_file new_rows
  printf "OK: delete %s\n" "$NAME"
}

# 获取排他锁（用于写操作）。
acquire_exclusive_lock() {
  [[ -e "$FILE" ]] || err "$RC_FILE" "file not found: $FILE"
  [[ -f "$FILE" ]] || err "$RC_FILE" "not a regular file: $FILE"
  [[ -r "$FILE" ]] || err "$RC_FILE" "file is not readable: $FILE"

  # 锁定目标名单文件本身，不创建额外锁文件。
  exec {lock_fd}< "$FILE" || err "$RC_LOCK" "cannot open file for lock: $FILE"
  flock -x -w 5 "$lock_fd" || err "$RC_LOCK" "cannot acquire lock on file: $FILE"
}

# 主流程：参数校验 -> (读操作直接执行) -> 写操作加锁后执行。
main() {
  parse_args "$@"

  if [[ "$OP_STATUS" -eq 1 ]]; then
    load_file
    parse_table
    validate_data_rows
    do_status
    exit "$RC_OK"
  fi

  if [[ "$OP_FIND" -eq 1 ]]; then
    load_file
    parse_table
    validate_data_rows
    do_find
    exit "$RC_OK"
  fi

  if [[ "$OP_INIT" -eq 1 ]]; then
    load_file
    parse_table
    validate_data_rows
    do_init
    exit "$RC_OK"
  fi

  if [[ "$OP_COMPACT" -eq 1 ]]; then
    load_file
    parse_table
    validate_data_rows
    do_compact
    exit "$RC_OK"
  fi

  acquire_exclusive_lock
  load_file
  parse_table
  validate_data_rows

  if [[ "$OP_REPLACE" -eq 1 ]]; then
    do_replace
  elif [[ "$OP_ADD" -eq 1 ]]; then
    do_add
  elif [[ "$OP_DELETE" -eq 1 ]]; then
    do_delete
  else
    err "$RC_INTERNAL" "unexpected operation state"
  fi
}

main "$@"
