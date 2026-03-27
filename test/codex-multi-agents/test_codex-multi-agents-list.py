"""codex-multi-agents-list.sh tests.

创建者: 榕
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖名单脚本的读取、查询、添加、修改、删除、初始化、压缩上下文与错误返回码路径。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路功能实现为 shell 脚本，当前任务不使用 pytest-cov 统计覆盖率。
- 达标判定: shell 实现按规则豁免 `95%` 覆盖率达标线。
- 当前以 `TC-001..022` 对应测试作为覆盖基线。

覆盖率命令:
- N/A（shell 脚本实现，当前任务不使用 pytest-cov 统计覆盖率）

使用示例:
- pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py

关联文件:
- 功能实现: [skills/codex-multi-agents/scripts/codex-multi-agents-list.sh](skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)
- Spec 文档: [spec/codex-multi-agents/scripts/codex-multi-agents-list.md](spec/codex-multi-agents/scripts/codex-multi-agents-list.md)
- 测试文件: [test/codex-multi-agents/test_codex-multi-agents-list.py](test/codex-multi-agents/test_codex-multi-agents-list.py)
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-list.sh"

HEADER = "| 姓名 | 状态 | 会话 | 启动类型 | agent session | 介绍 | 提示词 | 归档文件 | 职责 |"
SEP = "|---|---|---|---|---|---|---|---|---|"


def make_row(
    name: str,
    status: str = "free",
    session: str = "",
    startup_type: str = "",
    agent_session: str = "",
    intro: str = "",
    prompt: str = "",
    archive: str = "",
    duty: str = "",
) -> str:
    """生成标准 agents Markdown 行，确保列数与表头一致。

    创建者: 榕
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按固定列顺序拼接一行 agents Markdown 数据。

    使用示例:
    - make_row("小明")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
    - test: test/codex-multi-agents/test_codex-multi-agents-list.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
    """
    return f"| {name} | {status} | {session} | {startup_type} | {agent_session} | {intro} | {prompt} | {archive} | {duty} |"


def write_agents_file(path: Path, rows: list[str] | None = None, header: str = HEADER) -> None:
    """写入测试专用名单文件，默认带两名人员。

    创建者: 榕
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成包含表头与数据行的测试名单文件。

    使用示例:
    - write_agents_file(Path("agents-lists.md"))

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
    - test: test/codex-multi-agents/test_codex-multi-agents-list.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
    """
    if rows is None:
        rows = [
            make_row("小明", "free", "xiaoming", "codex", "agent-xiaoming", "擅长分发任务", "./prompt.md", "./log/", "任务分发"),
            make_row("李白", "doing", "libai", "claude", "agent-libai"),
        ]

    text = "\n".join(
        [
            "# Agents 名单",
            "",
            header,
            SEP,
            *rows,
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。

    创建者: 榕
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 subprocess 方式执行脚本并返回结果对象。

    使用示例:
    - run_script("-file=agents-lists.md", "-status")

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
    - test: test/codex-multi-agents/test_codex-multi-agents-list.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
    """
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def write_fake_tmux(bin_dir: Path, state_dir: Path, sessions: list[str] | None = None) -> Path:
    """写入 fake tmux，用于验证 -init/-compact 的会话检查与 send-keys 调用。

    创建者: 榕
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造临时 tmux 脚本，记录 send-keys 调用并模拟会话存在性。

    使用示例:
    - write_fake_tmux(Path("bin"), Path("state"), sessions=["xiaoming"])

    关联文件:
    - spec: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
    - test: test/codex-multi-agents/test_codex-multi-agents-list.py
    - 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
    """
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
    [[ -n "$target" ]] || exit 2
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
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_tmux.chmod(0o755)
    return calls_file


# TC-001
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -status 正常读取名单并输出表头与数据，返回码为 0。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_status_outputs_table_and_returns_0
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_status_outputs_table_and_returns_0(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(f"-file={agents_file}", "-status")

    assert result.returncode == 0
    assert "姓名" in result.stdout
    assert "小明" in result.stdout
    assert "李白" in result.stdout
    assert result.stderr == ""


# TC-002
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -find 查询字段成功时返回字段值与 RC=0。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_find_field_success
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_find_field_success(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(f"-file={agents_file}", "-find", "-name=小明", "-key=归档文件")

    assert result.returncode == 0
    assert result.stdout.strip() == "./log/"
    assert result.stderr == ""


# TC-003
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -find 查询不存在人员时返回 RC=3 并输出错误信息。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_find_missing_agent_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_find_missing_agent_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(f"-file={agents_file}", "-find", "-name=不存在", "-key=归档文件")

    assert result.returncode == 3
    assert "agent not found: 不存在" in result.stderr


# TC-004
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -add 成功新增人员并生成会话字段。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_add_agent_success
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_add_agent_success(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(f"-file={agents_file}", "-add", "-name=王五", "-type=codex")
    updated = agents_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: add 王五" in result.stdout
    assert "| 王五 |" in updated

    added_line = next(line for line in updated.splitlines() if line.startswith("| 王五 |"))
    cells = [cell.strip() for cell in added_line.strip().strip("|").split("|")]
    session = cells[2]
    startup_type = cells[3]
    agent_session = cells[4]
    assert session != ""
    assert all(ord(ch) < 128 for ch in session)
    assert re.search(r"[\u4e00-\u9fff]", session) is None
    assert session not in {"xiaoming", "libai"}
    assert startup_type == "codex"
    assert agent_session != ""
    assert all(ord(ch) < 128 for ch in agent_session)
    assert re.search(r"[\u4e00-\u9fff]", agent_session) is None
    assert agent_session not in {"agent-xiaoming", "agent-libai"}


# TC-005
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -add 添加同名人员时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_add_duplicate_agent_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_add_duplicate_agent_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script("-file", str(agents_file), "-add", "-name", "小明", "-type", "codex")

    assert result.returncode == 3
    assert "agent already exists: 小明" in result.stderr


# TC-006
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -replace 修改字段成功并写回文件。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_replace_field_success
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_replace_field_success(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(
        f"-file={agents_file}",
        "-replace",
        "-name=小明",
        "-key=状态",
        "-value=ready",
    )
    updated = agents_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: replace 小明 状态" in result.stdout
    assert "| 小明 | ready |" in updated


# TC-007
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -replace 试图修改姓名字段时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_replace_name_field_is_immutable
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_replace_name_field_is_immutable(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(
        "-file",
        str(agents_file),
        "-replace",
        "-name",
        "小明",
        "-key",
        "姓名",
        "-value",
        "新名字",
    )

    assert result.returncode == 3
    assert "field '姓名' is immutable and cannot be modified" in result.stderr


# TC-008
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -replace 修改非法字段时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_replace_unknown_field_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_replace_unknown_field_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(
        "-file",
        str(agents_file),
        "-replace",
        "-name",
        "小明",
        "-key",
        "不存在字段",
        "-value",
        "x",
    )

    assert result.returncode == 3
    assert "invalid field name: 不存在字段" in result.stderr


# TC-009
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -delete 删除人员成功并写回文件。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_delete_agent_success
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_delete_agent_success(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(f"-file={agents_file}", "-delete", "-name=李白")
    updated = agents_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: delete 李白" in result.stdout
    assert "| 李白 |" not in updated


# TC-010
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -delete 删除不存在人员时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_delete_missing_agent_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_delete_missing_agent_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script("-file", str(agents_file), "-delete", "-name", "不存在")

    assert result.returncode == 3
    assert "agent not found: 不存在" in result.stderr


# TC-011
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证参数缺失时返回 RC=1 并提示错误。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_argument_error_returns_rc1
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_argument_error_returns_rc1(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script("-file", str(agents_file), "-replace", "-name", "小明", "-key", "状态")

    assert result.returncode == 1
    assert "-replace requires -value" in result.stderr


# TC-012
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证文件不存在时返回 RC=2。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_file_not_found_returns_rc2
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_file_not_found_returns_rc2(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"

    result = run_script("-file", str(missing), "-status")

    assert result.returncode == 2
    assert "file not found" in result.stderr


# TC-013
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证表头缺少姓名列时返回 RC=2。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_invalid_table_missing_name_column_returns_rc2
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_invalid_table_missing_name_column_returns_rc2(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    bad_header = "| 状态 | 会话 | 启动类型 | agent session | 介绍 | 提示词 | 归档文件 | 职责 |"
    rows = ["| free | s1 | codex | a-s1 | intro | prompt | archive | 实施 |"]
    write_agents_file(agents_file, rows=rows, header=bad_header)

    result = run_script("-file", str(agents_file), "-status")

    assert result.returncode == 2
    assert "missing required column '姓名'" in result.stderr


# TC-014
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证名单姓名重复时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_duplicate_name_in_file_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_duplicate_name_in_file_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    rows = [
        make_row("小明", "free"),
        make_row("小明", "doing"),
    ]
    write_agents_file(agents_file, rows=rows)

    result = run_script("-file", str(agents_file), "-status")

    assert result.returncode == 3
    assert "duplicate 姓名 found: 小明" in result.stderr


# TC-015
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证写锁冲突时返回 RC=4。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_lock_conflict_returns_rc4
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_lock_conflict_returns_rc4(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)
    with agents_file.open("r", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_script("-file", str(agents_file), "-add", "-name", "并发测试", "-type", "codex")

    assert result.returncode == 4
    assert "cannot acquire lock" in result.stderr


# TC-016
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -replace 支持写入空值。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_replace_supports_empty_value
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_replace_supports_empty_value(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(
        f"-file={agents_file}",
        "-replace",
        "-name=小明",
        "-key=状态",
        "-value=",
    )
    updated = agents_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: replace 小明 状态" in result.stdout
    assert "| 小明 |  | xiaoming |" in updated


# TC-017
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -status 在写锁占用时仍可读取并返回 RC=0。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_status_ignores_lock_and_returns_rc0
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_status_ignores_lock_and_returns_rc0(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)
    with agents_file.open("r", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_script(f"-file={agents_file}", "-status")

    assert result.returncode == 0
    assert "姓名" in result.stdout
    assert "小明" in result.stdout
    assert result.stderr == ""


# TC-018
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -status 能读取缺少新增尾列的历史行。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_status_accepts_rows_missing_new_tail_column
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_status_accepts_rows_missing_new_tail_column(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    # 历史数据行缺少新增“职责”列，脚本应补空并正常读取。
    legacy_row_without_duty = "| 老王 | free | oldsess | codex | agent-old | intro | prompt | archive |"
    write_agents_file(agents_file, rows=[legacy_row_without_duty])

    result = run_script(f"-file={agents_file}", "-status")

    assert result.returncode == 0
    assert "老王" in result.stdout
    assert "职责" in result.stdout


# TC-019
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -init 会话存在时发送初始化消息并返回 RC=0。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_init_agent_sends_message_success
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_init_agent_sends_message_success(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["xiaoming"])
    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(f"-file={agents_file}", "-init", "-name=小明", env=env)
    calls = calls_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: init 小明" in result.stdout
    assert "send:xiaoming:" in calls
    assert "你的名字叫做小明" in calls
    assert "./prompt.md" in calls
    assert "你的工作树为" not in calls
    assert "./log/" in calls


# TC-020
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -init 目标会话不存在时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_init_agent_missing_session_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_init_agent_missing_session_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(f"-file={agents_file}", "-init", "-name=小明", env=env)

    assert result.returncode == 3
    assert "target session not found: xiaoming" in result.stderr


# TC-021
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -compact 会话存在时发送压缩与回报指令并返回 RC=0。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_compact_agent_sends_compact_and_report
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_compact_agent_sends_compact_and_report(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["xiaoming"])
    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(f"-file={agents_file}", "-compact", "-name=小明", env=env)
    calls = calls_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: compact 小明" in result.stdout
    assert "send:xiaoming:/compact:" in calls
    assert "你的名字叫做小明" in calls
    assert "回报管理员" in calls


# TC-022
# 创建者: 榕
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 13:46:50 +0800
# 最近一次运行成功时间: 2026-03-22 13:46:50 +0800
# 测试目的: 验证 -compact 目标会话不存在时返回 RC=3。
# 使用示例: pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py -k test_compact_agent_missing_session_returns_rc3
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-list.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-list.md
# 对应测试文件路径: test/codex-multi-agents/test_codex-multi-agents-list.py
def test_compact_agent_missing_session_returns_rc3(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(f"-file={agents_file}", "-compact", "-name=小明", env=env)

    assert result.returncode == 3
    assert "target session not found: xiaoming" in result.stderr
