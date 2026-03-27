"""codex-multi-agents-task.sh tests.

创建者: 榕
最后一次更改: 神秘人

功能说明:
- 覆盖 task 脚本的任务分发、完成、暂停、继续、改派、新建、状态查询与错误返回码路径。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路的功能实现为 shell 脚本 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`，`pytest-cov` 无法直接采集脚本覆盖率，执行覆盖率命令会得到 `no-data-collected`。
- 达标判定: shell 实现按规则豁免 `95%` 覆盖率达标线。
- 当前以 `TC-001..025` 共 25 条测试用例作为覆盖基线，覆盖分发、分发前初始化、分发消息发送、完成、暂停、继续、改派、新建、状态查询、文件错误、结构错误与锁冲突路径。

覆盖率命令:
- `pytest -q --cov=skills/codex-multi-agents/scripts/codex-multi-agents-task.sh --cov-branch --cov-report=term-missing test/codex-multi-agents/test_codex-multi-agents-task.py`
- 功能校验命令: `pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`

关联文件:
- 功能实现: `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`
- Spec 文档: `spec/codex-multi-agents/scripts/codex-multi-agents-task.md`
- 测试文件: `test/codex-multi-agents/test_codex-multi-agents-task.py`

使用示例:
- `pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-task.sh"


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。"""
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def row_running(
    task_id: str,
    owner: str,
    created_at: str,
    worktree: str,
    desc: str,
    assignee: str,
    status: str,
    guide: str = "",
    record: str = "",
) -> str:
    return f"| {task_id} | {owner} | {created_at} | {worktree} | {desc} | {assignee} | {status} | {guide} | {record} |"


def row_list(
    task_id: str,
    owner: str,
    created_at: str,
    worktree: str,
    desc: str,
    assignee: str = "",
    record: str = "",
) -> str:
    return f"| {task_id} | {owner} | {created_at} | {worktree} | {desc} | {assignee} | {record} |"


def agent_row(name: str, status: str = "free") -> str:
    return f"| {name} | {status} | {name}-session | codex | agent-{name} | 简介 | ./prompt.md | ./archive.md | 执行 |"


def write_agents_file(path: Path, rows: list[str] | None = None) -> None:
    """写入标准 agents-lists.md 测试文件。"""
    if rows is None:
        rows = [
            agent_row("worker-a", "free"),
            agent_row("worker-b", "busy"),
        ]

    text = "\n".join(
        [
            "# Agents 名单",
            "",
            "| 姓名 | 状态 | 会话 | 启动类型 | agent session | 介绍 | 提示词 | 归档文件 | 职责 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def write_fake_tmux(bin_dir: Path, state_dir: Path, sessions: list[str] | None = None) -> Path:
    """写入 fake tmux 可执行文件，用于拦截 dispatch 内部触发的 talk。"""
    sessions = sessions or []
    bin_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    sessions_file = state_dir / "sessions.txt"
    calls_file = state_dir / "calls.log"
    sessions_file.write_text("\n".join(sessions) + ("\n" if sessions else ""), encoding="utf-8")
    calls_file.write_text("", encoding="utf-8")

    fake_tmux = bin_dir / "tmux"
    fake_tmux.write_text(
        """#!/usr/bin/env bash
set -u
state_dir="${FAKE_TMUX_STATE_DIR:?}"
sessions_file="$state_dir/sessions.txt"
calls_file="$state_dir/calls.log"
cmd="${1-}"
[[ -n "$cmd" ]] || exit 2
shift || true

case "$cmd" in
  has-session)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    grep -Fxq "$target" "$sessions_file"
    ;;
  send-keys)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    msg="${3-}"
    key="${4-}"
    echo "send:$target:$msg:$key" >> "$calls_file"
    ;;
  *)
    exit 0
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_tmux.chmod(0o755)
    return calls_file


def write_todo_file(path: Path, running_rows: list[str] | None = None, list_rows: list[str] | None = None) -> None:
    """写入标准 TODO.md 测试文件。"""
    if running_rows is None:
        running_rows = [
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "worker-b", "进行中", "xxx", "./log/ex2.md"),
        ]
    if list_rows is None:
        list_rows = [
            row_list("EX-3", "苏轼", "2026-03-08 16:30:00 +0800", "", "删除 tmp/demo.txt", "", "./log/ex3.md"),
        ]

    text = "\n".join(
        [
            "## 正在执行的任务",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *running_rows,
            "",
            "## 需要用户确认的事项",
            "",
            "| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- |",
            "| U-1 | 2026-03-08 16:00:00 +0800 | . | 描述 | 未确认 | ./log/u1.md |",
            "",
            "## 任务列表",
            "",
            "| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *list_rows,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def parse_section_rows(text: str, heading: str) -> list[list[str]]:
    """解析指定标题下的首个 markdown 表格数据行。"""
    lines = text.splitlines()
    section_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == heading:
            section_idx = i
            break
    if section_idx < 0:
        return []

    section_end = len(lines)
    for i in range(section_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            section_end = i
            break

    header_idx = -1
    for i in range(section_idx + 1, max(section_end - 1, section_idx + 1)):
        s1 = lines[i].strip()
        s2 = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if s1.startswith("|") and s1.endswith("|") and s2.startswith("|") and "---" in s2:
            header_idx = i
            break
    if header_idx < 0:
        return []

    rows: list[list[str]] = []
    idx = header_idx + 2
    while idx < section_end:
        s = lines[idx].strip()
        if not (s.startswith("|") and s.endswith("|")):
            break
        rows.append([c.strip() for c in s[1:-1].split("|")])
        idx += 1

    return rows


def get_agent_status(path: Path, name: str) -> str:
    rows = parse_section_rows(path.read_text(encoding="utf-8"), "# Agents 名单")
    for row in rows:
        if row[0] == name:
            return row[1]
    raise AssertionError(f"agent not found: {name}")


# TC-001
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -dispatch 成功将任务从任务列表移入正在执行并写入指派/状态。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    assert "OK: replace worker-a 状态" in result.stdout
    assert any(
        r[0] == "EX-3"
        and r[1] == "苏轼"
        and r[5] == "worker-a"
        and r[6] == "进行中"
        and r[8] == "./log/ex3.md"
        and r[3] == ""
        and r[2] != ""
        for r in running_rows
    )
    assert not any(r[0] == "EX-3" for r in list_rows)
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-002
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -dispatch 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-dispatch", "-task_id", "BAD", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in task list: BAD" in result.stderr


# TC-003
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -done 成功移除任务并写入 DONE.md。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_task_moves_to_done_file_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy")])
    log_path = "./agents/codex-multi-agents/log/task-EX-1.log"

    result = run_script("-file", str(todo), "-done", "-task_id", "EX-1", "-log", log_path, "-agents-list", str(agents))
    todo_text = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(todo_text, "## 正在执行的任务")

    done_file = tmp_path / "DONE.md"
    done_text = done_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: done EX-1" in result.stdout
    assert "OK: replace worker-a 状态" in result.stdout
    assert not any(r[0] == "EX-1" for r in running_rows)

    assert done_file.exists()
    assert "| EX-1 |" in done_text
    assert "| 已完成 |" in done_text
    assert log_path in done_text
    assert re.search(r"\| EX-1 \|.*\| 已完成 \| \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4} \|", done_text)
    assert get_agent_status(agents, "worker-a") == "free"


# TC-004
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -done 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_done_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-done", "-task_id", "BAD", "-log", "./log/bad.log", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-005
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -pause 成功将任务状态更新为 暂停。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_pause_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy")])

    result = run_script("-file", str(todo), "-pause", "-task_id", "EX-2", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: pause EX-2" in result.stdout
    assert "OK: replace worker-b 状态" in result.stdout
    assert any(r[0] == "EX-2" and r[6] == "暂停" for r in running_rows)
    assert get_agent_status(agents, "worker-b") == "free"


# TC-006
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -pause 任务不存在返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_pause_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-pause", "-task_id", "BAD", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-007
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -new 带指派创建任务并写入任务列表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_task_with_assignee_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(
        "-file",
        str(todo),
        "-new",
        "-info",
        "实现任务调度器告警",
        "-to",
        "worker-b",
        "-from",
        "李白",
        "-worktree",
        "repo-x",
        "-log",
        "./log/record-1.log",
    )
    content = todo.read_text(encoding="utf-8")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert re.search(r"OK: new T-\d{8}-[0-9a-f]{8}", result.stdout)
    assert any(
        r[4] == "实现任务调度器告警"
        and r[5] == "worker-b"
        and r[1] == "李白"
        and r[3] == "repo-x"
        and r[6] == "./log/record-1.log"
        and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}", r[2] or "")
        for r in list_rows
    )


# TC-008
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -new 不带指派创建任务并写入任务列表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_new_task_without_assignee_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-new", "-info", "补充单元测试")
    content = todo.read_text(encoding="utf-8")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 0
    assert re.search(r"OK: new T-\d{8}-[0-9a-f]{8}", result.stdout)
    assert any(
        r[4] == "补充单元测试"
        and r[5] == ""
        and r[1] == ""
        and r[3] == ""
        and r[6] == ""
        and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}", r[2] or "")
        for r in list_rows
    )


# TC-009
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证缺少必填参数返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_argument_error_returns_rc1(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-done", "-task_id", "EX-1")

    assert result.returncode == 1
    assert "-done requires -log" in result.stderr


# TC-010
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 TODO 文件不存在返回 RC=2。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_file_not_found_returns_rc2(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"

    result = run_script("-file", str(missing), "-new", "-info", "desc")

    assert result.returncode == 2
    assert "file not found" in result.stderr


# TC-011
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证表结构不合法返回 RC=2。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_invalid_todo_structure_returns_rc2(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    todo.write_text(
        "\n".join(
            [
                "## 非法任务段落",
                "",
                "| A | B |",
                "| --- | --- |",
                "| 1 | 2 |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_script("-file", str(todo), "-new", "-info", "desc")

    assert result.returncode == 2
    assert "invalid table format" in result.stderr


# TC-012
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证锁冲突时返回 RC=4。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_lock_conflict_returns_rc4(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    with todo.open("r", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_script("-file", str(todo), "-dispatch", "-task_id", "EX-3", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 4
    assert "cannot acquire lock" in result.stderr


# TC-013
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -status -doing 输出正在执行任务表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_doing_outputs_running_table(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status", "-doing")

    assert result.returncode == 0
    assert "正在执行的任务" not in result.stdout
    assert "任务列表" not in result.stdout
    assert "EX-1" in result.stdout
    assert "EX-3" not in result.stdout


# TC-014
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:16:41 +0800
# 最近一次运行成功时间: 2026-03-22 17:16:41 +0800
# 测试目的: 验证 -status -task-list 输出任务列表表。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_task_list_outputs_list_table(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status", "-task-list")

    assert result.returncode == 0
    assert "正在执行的任务" not in result.stdout
    assert "任务列表" not in result.stdout
    assert "EX-3" in result.stdout
    assert "EX-1" not in result.stdout


# TC-015
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-25 03:41:48 +0800
# 最近一次运行成功时间: 2026-03-25 03:41:48 +0800
# 测试目的: 验证 -status 参数组合错误返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_status_requires_exactly_one_mode(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script(str(todo), "-file", "-status")
    assert result.returncode == 1
    assert "-status requires exactly one of -doing/-task-list" in result.stderr

    result = run_script(str(todo), "-file", "-status", "-doing", "-task-list")
    assert result.returncode == 1
    assert "-status requires exactly one of -doing/-task-list" in result.stderr


# TC-016
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-25 03:41:48 +0800
# 最近一次运行成功时间: 2026-03-25 03:41:48 +0800
# 测试目的: 验证 -dispatch 携带 -message 时，仍会先执行一次 -init，再调用 tmux 对话脚本向目标会话发消息。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_with_message_sends_talk_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    config = tmp_path / "config.txt"
    talk_log = tmp_path / "logs" / "talk.log"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a-session"])
    write_todo_file(todo)
    write_agents_file(agents)
    config.write_text(
        "\n".join(
            [
                "ROOT_NAME=神秘人",
                f"LOG_DIR={talk_log.parent}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_CONFIG"] = str(config)
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        "-message",
        "请处理任务 EX-3，完成后回报。",
        env=env,
    )

    assert result.returncode == 0
    assert "OK: init worker-a" in result.stdout
    assert "OK: dispatch EX-3 -> worker-a" in result.stdout
    assert result.stdout.index("OK: init worker-a") < result.stdout.index("OK: dispatch EX-3 -> worker-a")
    assert "OK: talk 神秘人 -> worker-a (worker-a-session)" in result.stdout
    calls_text = calls_file.read_text(encoding="utf-8")
    assert "你的名字叫做worker-a" in calls_text
    assert calls_text.index("你的名字叫做worker-a") < calls_text.index("@神秘人向@worker-a发起会话: 请处理任务 EX-3，完成后回报。")
    assert "send:worker-a-session:@神秘人向@worker-a发起会话: 请处理任务 EX-3，完成后回报。:" in calls_text
    assert "@神秘人向@worker-a发起会话: 请处理任务 EX-3，完成后回报。" in talk_log.read_text(encoding="utf-8")


# TC-017
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 17:24:46 +0800
# 最近一次运行成功时间: 2026-03-22 17:24:46 +0800
# 测试目的: 验证 -dispatch 携带 -message 时，即使分发前 -init 失败，仍会保留已提交的分发结果并在消息发送失败时返回错误。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_with_message_failure_keeps_dispatch_result(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    config = tmp_path / "config.txt"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    write_todo_file(todo)
    write_agents_file(agents)
    config.write_text("ROOT_NAME=神秘人\nLOG_DIR={}\n".format(tmp_path / "logs"), encoding="utf-8")

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["CODEX_MULTI_AGENTS_CONFIG"] = str(config)
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        "-message",
        "请处理任务 EX-3",
        env=env,
    )
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")
    list_rows = parse_section_rows(content, "## 任务列表")

    assert result.returncode == 3
    assert "WARN: dispatch init failed for worker-a:" in result.stderr
    assert "target session not found: worker-a-session" in result.stderr
    assert "dispatch succeeded but message delivery failed for task EX-3" in result.stderr
    assert any(r[0] == "EX-3" and r[5] == "worker-a" and r[6] == "进行中" for r in running_rows)
    assert not any(r[0] == "EX-3" for r in list_rows)
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-018
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-25 03:41:48 +0800
# 最近一次运行成功时间: 2026-03-25 03:41:48 +0800
# 测试目的: 验证 -dispatch 在真正分发前会固定调用一次 list -init 向目标会话发送角色信息提醒。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_dispatch_runs_init_before_dispatch(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a-session"])
    write_todo_file(todo)
    write_agents_file(agents)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    result = run_script(
        "-file",
        str(todo),
        "-dispatch",
        "-task_id",
        "EX-3",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents),
        env=env,
    )

    assert result.returncode == 0
    assert "OK: init worker-a" in result.stdout
    assert result.stdout.index("OK: init worker-a") < result.stdout.index("OK: dispatch EX-3 -> worker-a")
    assert "你的名字叫做worker-a" in calls_file.read_text(encoding="utf-8")
    assert get_agent_status(agents, "worker-a") == "busy"


# TC-019
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 成功将暂停任务恢复为进行中并同步角色状态为 busy。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "worker-b", "暂停", "xxx", "./log/ex2.md"),
        ],
    )
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "free")])

    result = run_script("-file", str(todo), "-continue", "-task_id", "EX-2", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: continue EX-2" in result.stdout
    assert "OK: replace worker-b 状态" in result.stdout
    assert any(r[0] == "EX-2" and r[6] == "进行中" for r in running_rows)
    assert get_agent_status(agents, "worker-b") == "busy"


# TC-020
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 任务不存在时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-continue", "-task_id", "BAD", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-021
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 仅允许继续状态为暂停的任务。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_requires_paused_status(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-continue", "-task_id", "EX-2", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task status is not paused: EX-2" in result.stderr


# TC-022
# 创建者: 榕
# 最后一次更改: 榕
# 最近一次运行测试时间: 2026-03-26 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 00:00:00 +0800
# 测试目的: 验证 -continue 缺少 -agents-list 参数时返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_continue_requires_agents_list(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-continue", "-task_id", "EX-2")

    assert result.returncode == 1
    assert "-continue requires -agents-list" in result.stderr


# TC-023
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-26 11:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 11:00:00 +0800
# 测试目的: 验证 -reassign 成功更新任务指派并同步旧/新角色状态。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_task_success(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(
        todo,
        running_rows=[
            row_running("EX-1", "李白", "2026-03-08 16:10:00 +0800", ".", "创建 src", "worker-a", "进行中", "xxx", "./log/ex1.md"),
            row_running("EX-2", "杜甫", "2026-03-08 16:20:00 +0800", ".", "创建 test", "worker-b", "进行中", "xxx", "./log/ex2.md"),
        ],
    )
    write_agents_file(agents, [agent_row("worker-a", "busy"), agent_row("worker-b", "busy"), agent_row("worker-c", "free")])

    result = run_script("-file", str(todo), "-reassign", "-task_id", "EX-2", "-to", "worker-c", "-agents-list", str(agents))
    content = todo.read_text(encoding="utf-8")
    running_rows = parse_section_rows(content, "## 正在执行的任务")

    assert result.returncode == 0
    assert "OK: reassign EX-2 -> worker-c" in result.stdout
    assert any(r[0] == "EX-2" and r[5] == "worker-c" for r in running_rows)
    assert get_agent_status(agents, "worker-a") == "busy"
    assert get_agent_status(agents, "worker-b") == "free"
    assert get_agent_status(agents, "worker-c") == "busy"


# TC-024
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-26 11:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 11:00:00 +0800
# 测试目的: 验证 -reassign 任务不存在时返回 RC=3。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_missing_task_returns_rc3(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    agents = tmp_path / "agents-lists.md"
    write_todo_file(todo)
    write_agents_file(agents)

    result = run_script("-file", str(todo), "-reassign", "-task_id", "BAD", "-to", "worker-a", "-agents-list", str(agents))

    assert result.returncode == 3
    assert "task not found in running list: BAD" in result.stderr


# TC-025
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-26 11:00:00 +0800
# 最近一次运行成功时间: 2026-03-26 11:00:00 +0800
# 测试目的: 验证 -reassign 缺少 -agents-list 参数时返回 RC=1。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-task.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-task.md
def test_reassign_requires_agents_list(tmp_path: Path) -> None:
    todo = tmp_path / "TODO.md"
    write_todo_file(todo)

    result = run_script("-file", str(todo), "-reassign", "-task_id", "EX-2", "-to", "worker-a")

    assert result.returncode == 1
    assert "-reassign requires -agents-list" in result.stderr
