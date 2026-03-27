"""codex-multi-agents-tmux.sh tests.

创建者: 榕
最后一次更改: 神秘人

功能说明:
- 覆盖 tmux 脚本的 talk / init-env / wake 主流程与错误返回码路径。

关联文件:
- 功能实现: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
- Spec 文档: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
- 测试文件: test/codex-multi-agents/test_codex-multi-agents-tmux.py

使用示例:
- pytest -q test/codex-multi-agents/test_codex-multi-agents-tmux.py

覆盖率信息:
- `skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh` 为 `sh` 实现，按 `AGENTS.md` 可豁免 `95%` 覆盖率达标线。
- 2026-03-22 执行 `pytest -q test/codex-multi-agents/test_codex-multi-agents-tmux.py` 前，先补齐文件级覆盖率说明与测试注释字段。
- 2026-03-22 尝试使用 `pytest-cov` 采集 shell 脚本覆盖率时，预期仅记录豁免结论，不以 Python 百分比覆盖率作为达标依据。

覆盖率命令:
- 豁免：`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh` 为 `sh` 实现，不适用 Python 模块覆盖率统计。
- 功能校验命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-tmux.py`
"""

from __future__ import annotations

import fcntl
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh"


def write_agents_file(path: Path, rows: list[str] | None = None) -> None:
    """写入供 -init-env / -wake 测试使用的名单文件。"""
    header = "| 姓名 | 状态 | 会话 | 启动类型 | agent session | worktree | 介绍 | 提示词 | 归档文件 | 职责 |"
    sep = "|---|---|---|---|---|---|---|---|---|---|"
    if rows is None:
        rows = [
            "| 小明 | free | xiaoming | codex | agent-xiaoming | worktrees/xiaoming | intro | prompt.md | archive/ | duty |",
            "| 李白 | free | libai | claude | agent-libai | worktrees/libai | intro | prompt.md | archive/ | duty |",
        ]
    text = "\n".join(["# Agents 名单", "", header, sep, *rows, ""])
    path.write_text(text, encoding="utf-8")


def write_fake_tmux(bin_dir: Path, state_dir: Path, sessions: list[str] | None = None) -> Path:
    """写入 fake tmux 可执行文件，用于拦截并记录 tmux 调用。"""
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
    if grep -Fxq "$target" "$sessions_file" 2>/dev/null; then
      exit 0
    fi
    exit 1
    ;;
  attach)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    echo "attach:$target" >> "$calls_file"
    exit 0
    ;;
  new)
    [[ "${1-}" == "-s" ]] || exit 2
    target="${2-}"
    echo "$target" >> "$sessions_file"
    echo "new:$target" >> "$calls_file"
    exit 0
    ;;
  new-session)
    if [[ "${1-}" == "-d" ]]; then
      shift
    fi
    [[ "${1-}" == "-s" ]] || exit 2
    target="${2-}"
    echo "$target" >> "$sessions_file"
    echo "new-session:$target" >> "$calls_file"
    exit 0
    ;;
  send-keys)
    [[ "${1-}" == "-t" ]] || exit 2
    target="${2-}"
    msg="${3-}"
    key="${4-}"
    echo "send:$target:$msg:$key" >> "$calls_file"
    exit 0
    ;;
  *)
    echo "unknown:$cmd" >> "$calls_file"
    exit 2
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_tmux.chmod(0o755)
    return calls_file


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """调用待测 shell 脚本并返回执行结果。"""
    return subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


# TC-001
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-talk` 能通过 agents list 解析目标会话并发送格式化消息，同时向日志追加一行记录。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_send_and_append_log_success(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(
        agents_file,
        rows=[
            "| worker-a | free | worker-a | codex | agent-worker-a | worktrees/worker-a | intro | prompt.md | archive/ | duty |",
        ],
    )
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents_file),
        "-message",
        "请处理任务 T1",
        "-log",
        str(log_file),
        env=env,
    )
    calls = calls_file.read_text(encoding="utf-8")
    log_text = log_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: talk scheduler -> worker-a (worker-a)" in result.stdout
    assert calls.count("send:worker-a:@scheduler向@worker-a发起会话: 请处理任务 T1:") == 1
    assert calls.count("send:worker-a:ENTER:") == 1
    assert "@scheduler向@worker-a发起会话: 请处理任务 T1" in log_text


# TC-002
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-talk` 在 agents list 解析出的目标会话不存在时返回 `RC=3`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_target_session_not_found_returns_rc3(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(
        agents_file,
        rows=[
            "| worker-a | free | missing | codex | agent-worker-a | worktrees/worker-a | intro | prompt.md | archive/ | duty |",
        ],
    )
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents_file),
        "-message",
        "hello",
        "-log",
        str(log_file),
        env=env,
    )

    assert result.returncode == 3
    assert "target session not found: missing" in result.stderr


# TC-003
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-talk` 缺少 `-message` 时返回 `RC=1`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_missing_message_returns_rc1(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(
        agents_file,
        rows=[
            "| worker-a | free | worker-a | codex | agent-worker-a | worktrees/worker-a | intro | prompt.md | archive/ | duty |",
        ],
    )
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents_file),
        "-log",
        str(log_file),
        env=env,
    )

    assert result.returncode == 1
    assert "-talk requires -message" in result.stderr


# TC-004
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证运行环境缺少 `tmux` 时返回 `RC=2`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_tmux_not_found_returns_rc2(tmp_path: Path) -> None:
    empty_bin = tmp_path / "empty_bin"
    empty_bin.mkdir(parents=True, exist_ok=True)
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(
        agents_file,
        rows=[
            "| worker-a | free | worker-a | codex | agent-worker-a | worktrees/worker-a | intro | prompt.md | archive/ | duty |",
        ],
    )

    env = os.environ.copy()
    env["PATH"] = str(empty_bin)

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents_file),
        "-message",
        "hello",
        "-log",
        str(tmp_path / "talk.log"),
        env=env,
    )

    assert result.returncode == 2
    assert "tmux not found in PATH" in result.stderr


# TC-005
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-talk` 日志锁冲突时返回 `RC=4`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_lock_conflict_returns_rc4(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(
        agents_file,
        rows=[
            "| worker-a | free | worker-a | codex | agent-worker-a | worktrees/worker-a | intro | prompt.md | archive/ | duty |",
        ],
    )
    log_file = tmp_path / "talk.log"
    lock_path = Path(f"{log_file}.lock")
    lock_path.touch()

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    with lock_path.open("w", encoding="utf-8") as lock_fd:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run_script(
            "-talk",
            "-from",
            "scheduler",
            "-to",
            "worker-a",
            "-agents-list",
            str(agents_file),
            "-message",
            "hello",
            "-log",
            str(log_file),
            env=env,
        )

    assert result.returncode == 4
    assert "cannot acquire lock" in result.stderr


# TC-006
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-init-env` 能创建 codex 会话并发送 `/resume` 初始化命令。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_init_env_codex_creates_session_and_bootstraps(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=[])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-init-env",
        "-file",
        str(agents_file),
        "-name",
        "小明",
        env=env,
    )
    calls = calls_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: init-env 小明 (xiaoming)" in result.stdout
    assert "new-session:xiaoming" in calls
    assert calls.count("send:xiaoming:codex /resume agent-xiaoming:") == 1
    assert calls.count("send:xiaoming:codex:") == 0
    assert calls.count("send:xiaoming:/rename agent-xiaoming:") == 0
    assert calls.count("send:xiaoming:ENTER:") == 1


# TC-007
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-init-env` 在名单缺少目标角色时返回 `RC=3`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_init_env_missing_agent_returns_rc3(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=[])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-init-env",
        "-file",
        str(agents_file),
        "-name",
        "不存在",
        env=env,
    )

    assert result.returncode == 3
    assert "failed to read field" in result.stderr


# TC-008
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-wake` 能创建 codex 会话并发送 `codex` 与 `/rename` 命令。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_wake_codex_creates_session_and_resumes(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    calls_file = write_fake_tmux(bin_dir, state_dir, sessions=[])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-wake",
        "-file",
        str(agents_file),
        "-name",
        "小明",
        env=env,
    )
    calls = calls_file.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "OK: wake 小明 (xiaoming)" in result.stdout
    assert "new-session:xiaoming" in calls
    assert calls.count("send:xiaoming:codex:") == 1
    assert calls.count("send:xiaoming:/rename agent-xiaoming:") == 1
    assert calls.count("send:xiaoming:codex /resume agent-xiaoming:") == 0
    assert calls.count("send:xiaoming:/resume agent-xiaoming:") == 0
    assert calls.count("send:xiaoming:ENTER:") == 2


# TC-009
# 创建者: 榕
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 13:11:42 +0800
# 最近一次运行成功时间: 2026-03-22 13:11:42 +0800
# 测试目的: 验证 `-wake` 不接受对话参数并返回 `RC=1`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_wake_does_not_accept_talk_arguments(tmp_path: Path) -> None:
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(agents_file)

    result = run_script(
        "-wake",
        "-file",
        str(agents_file),
        "-name",
        "小明",
        "-message",
        "hello",
    )

    assert result.returncode == 1
    assert "-wake does not accept -from/-to/-message/-log" in result.stderr


# TC-010
# 创建者: 榕
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-22 18:25:00 +0800
# 最近一次运行成功时间: 2026-03-22 18:25:00 +0800
# 测试目的: 验证 `-talk` 在 agents list 不存在目标角色时返回 `RC=3`。
# 对应功能实现文件路径: skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh
# 对应 spec 文件路径: spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md
def test_talk_missing_target_agent_in_agents_list_returns_rc3(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    write_fake_tmux(bin_dir, state_dir, sessions=["worker-a"])
    agents_file = tmp_path / "agents-lists.md"
    write_agents_file(
        agents_file,
        rows=[
            "| other-worker | free | worker-a | codex | agent-other-worker | worktrees/other-worker | intro | prompt.md | archive/ | duty |",
        ],
    )
    log_file = tmp_path / "talk.log"

    env = os.environ.copy()
    env["FAKE_TMUX_STATE_DIR"] = str(state_dir)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = run_script(
        "-talk",
        "-from",
        "scheduler",
        "-to",
        "worker-a",
        "-agents-list",
        str(agents_file),
        "-message",
        "hello",
        "-log",
        str(log_file),
        env=env,
    )

    assert result.returncode == 3
    assert "failed to read field '会话' for agent: worker-a" in result.stderr
