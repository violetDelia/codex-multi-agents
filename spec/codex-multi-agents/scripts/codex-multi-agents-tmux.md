# codex-multi-agents-tmux.md

用于对 `codex-multi-agents` 的 tmux 会话进行消息发送与环境初始化。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-tmux.py`](../../../test/codex-multi-agents/test_codex-multi-agents-tmux.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh)

## [immutable]文件位置

- 脚本文件：[`skills/codex-multi-agents/scripts/codex-multi-agents-tmux`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh)

## 参数约定

- `-talk`：向目标会话发送消息并写入日志。
- `-init-env`：按名单信息初始化目标角色运行环境。
- `-wake`：按名单信息唤醒目标角色运行环境。
- `-from`：消息发送方标识。
- `-to`：消息接收方标识，仅用于消息格式化展示。
- `-agents-list`：agents 名单文件路径（用于 `-talk` 按 `-to` 解析目标会话）。
- `-message`：消息正文。
- `-log`：对话日志文件路径。
- `-file`：agents 名单文件路径（用于 `-init-env/-wake`）。
- `-name`：待初始化或唤醒的角色名（用于 `-init-env/-wake`）。

## 并发约束

- `-talk` 追加日志时必须使用 `flock` 文件锁，避免并发写入冲突。

## 功能

### 发送对话

命令：

```bash
codex-multi-agents-tmux.sh -talk -from "scheduler" -to "worker-a" -agents-list "./agents/codex-multi-agents/agents-lists.md" -message "请处理任务 T1" -log "./agents/codex-multi-agents/log/talk.log"
```

功能说明：

- [immutable]发送文本格式固定为：`@<from>向@<to>发起会话: <message>`。
- 使用 `-agents-list` 中目标角色 `-to` 对应的 `会话` 字段解析 tmux 目标会话名。
- [immutable]使用命令 `tmux send-keys -t <session-id> "<formatted_message>"` 向目标会话发送消息，等待一秒后，使用 `tmux send-keys -t <session-id> ENTER` 确保消息被收到。
- 同步向 `-log` 文件追加一行同内容消息。
- 若日志目录不存在，脚本会自动创建后再写入。

注意事项：

- `-from`、`-to`、`-agents-list`、`-message`、`-log` 均为必填参数。
- `-talk` 不再接受手工传入 `-session-id`；目标会话必须通过 `agents-lists.md` 自动解析。
- 目标会话不存在时返回数据错误（`RC=3`）。
- 目标角色不在名单中或 `会话` 字段为空时返回数据错误（`RC=3`）。
- 写日志时使用 `flock` 加锁，锁超时或冲突返回锁错误（`RC=4`）。


### 初始化环境

命令：

```bash
codex-multi-agents-tmux.sh -wake -file "agents-lists.md" -name xiaoming
```

功能说明：

- 通过名单文件读取目标角色 `会话`、`启动设置/启动类型`、`agent session` 字段。
- 执行 `tmux new-session -d -s <会话>` 创建会话。
  - [immutable]若启动类型为 `codex`，依次执行以下初始化命令,中间间隔"3"秒：
    - `tmux send-keys -t <会话> "codex"`
    - `tmux send-keys -t <会话> "/rename <agent session>"`
    - `tmux send-keys -t <会话> ENTER`
注意事项：

- `-file`、`-name` 为必填参数。
- `-wake` 不接受 `-from/-to/-message/-log` 参数。
- 若名单文件缺失、不可读或格式不合法，返回文件错误。
- 若角色不存在或关键字段读取失败，返回数据错误。

## 唤醒角色
```bash
codex-multi-agents-tmux.sh -init-env -file "agents-lists.md" -name xiaoming
```

功能说明：

- 通过名单文件读取目标角色 `会话`、`启动设置/启动类型`、`agent session` 字段。
- 执行 `tmux new-session -d -s <会话>` 创建会话。
  - [immutable]若启动类型为 `codex`，依次执行以下初始化命令,中间间隔"3"秒：
    - `tmux send-keys -t <会话> "codex /resume <agent session>"`
    - `tmux send-keys -t <会话> ENTER`
注意事项：

- `-file`、`-name` 为必填参数。
- `-init-env` 不接受 `-from/-to/-message/-log` 参数。
- 若名单文件缺失、不可读或格式不合法，返回文件错误。
- 若角色不存在或关键字段读取失败，返回数据错误。

## 返回与错误

### 成功返回说明

- 返回码：`0`
- 含义：命令执行成功，目标操作已完成。
- 输出：在标准输出（stdout）打印结果信息。

### 失败返回说明

- 返回码：`1`
- 含义：参数错误（参数缺失、参数组合非法、未知参数）。
- 输出：在标准错误（stderr）中打印参数错误原因。

- 返回码：`2`
- 含义：文件或环境错误（日志目录不可写、`tmux` 不可用）。
- 输出：在标准错误（stderr）中打印路径或环境错误原因。

- 返回码：`3`
- 含义：数据错误（目标会话不存在等）。
- 输出：在标准错误（stderr）中打印具体数据校验失败原因。

- 返回码：`4`
- 含义：并发或锁错误（日志文件加锁失败、锁超时、锁冲突）。
- 输出：在标准错误（stderr）中打印锁状态与处理建议。

- 返回码：`5`
- 含义：未分类内部错误（脚本执行异常）。
- 输出：在标准错误（stderr）中打印错误摘要。

## 测试

- 测试文件位置：[`test/codex-multi-agents/test_codex-multi-agents-tmux.py`](../../../test/codex-multi-agents/test_codex-multi-agents-tmux.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-tmux.py`

### 测试目标

- 验证 `-talk` 的消息格式、单次发送、日志目录自动创建与日志追加行为。
- 验证 `-init-env` 的名单读取、会话创建与 codex 初始化流程（含 3 秒间隔）。
- 验证 `-wake` 的名单读取、会话创建与 codex 唤醒流程（含 3 秒间隔）。
- 验证返回码约定：`0/1/2/3/4/5`。
- 验证并发锁冲突下的错误返回。

### 测试范围

- 命令行参数解析与参数组合校验。
- `send-keys` 发送内容格式与目标会话路由。
- 日志追加、目录创建与文件锁控制。
- 基于 agents 名单的字段读取、初始化链路与唤醒链路。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TC-001 | `-talk` | 正常发送并记日志 | agents list 中存在目标角色且目标会话存在，日志可写 | `-talk -from A -to B -agents-list F -message M -log L` | 返回码 `0`；发送格式正确且发送一次；日志新增一行 |
| TC-002 | `-talk` | 目标会话不存在 | agents list 中角色 `B` 的 `会话` 为 missing，tmux 中不存在该会话 | `-talk -from A -to B -agents-list F -message M -log L` | 返回码 `3`；报错会话不存在 |
| TC-003 | 参数校验 | 缺少必填参数 | 无 | `-talk -from A -to B -agents-list F -log L` | 返回码 `1`；报错缺少 `-message` |
| TC-004 | 环境校验 | tmux 不可用 | `PATH` 中无 tmux | `-talk -from A -to B -agents-list F -message M -log L` | 返回码 `2`；报错 `tmux not found` |
| TC-005 | 并发锁 | 日志锁冲突 | 另一个进程持有 `<log>.lock` | `-talk -from A -to B -agents-list F -message M -log L` | 返回码 `4`；报错无法加锁 |
| TC-006 | `-init-env` | codex 角色初始化成功 | 名单存在目标角色；会话不存在 | `-init-env -file F -name 小明` | 返回码 `0`；创建会话；`codex` 与 `/rename` 命令各发送一次（间隔 3 秒）并发送 `ENTER` |
| TC-007 | `-init-env` | 角色不存在 | 名单中不存在目标角色 | `-init-env -file F -name 不存在` | 返回码 `3`；报错读取字段失败 |
| TC-008 | `-wake` | codex 角色唤醒成功 | 名单存在目标角色；会话不存在 | `-wake -file F -name 小明` | 返回码 `0`；创建会话；`codex` 与 `/resume` 命令各发送一次（间隔 3 秒）并发送 `ENTER` |
| TC-009 | 参数校验 | `-wake` 混入对话参数 | 名单文件存在 | `-wake -file F -name 小明 -message M` | 返回码 `1`；报错 `-wake` 不接受对话参数 |
| TC-010 | `-talk` | 目标角色不在名单中 | agents list 中不存在角色 `B` | `-talk -from A -to B -agents-list F -message M -log L` | 返回码 `3`；报错读取 `会话` 字段失败 |

### 用例与自动化映射

- TC-001 -> `test_talk_send_and_append_log_success`
- TC-002 -> `test_talk_target_session_not_found_returns_rc3`
- TC-003 -> `test_talk_missing_message_returns_rc1`
- TC-004 -> `test_tmux_not_found_returns_rc2`
- TC-005 -> `test_talk_lock_conflict_returns_rc4`
- TC-006 -> `test_init_env_codex_creates_session_and_bootstraps`
- TC-007 -> `test_init_env_missing_agent_returns_rc3`
- TC-008 -> `test_wake_codex_creates_session_and_resumes`
- TC-009 -> `test_wake_does_not_accept_talk_arguments`
- TC-010 -> `test_talk_missing_target_agent_in_agents_list_returns_rc3`
