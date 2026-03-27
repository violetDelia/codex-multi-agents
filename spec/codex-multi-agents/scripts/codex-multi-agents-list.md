# codex-multi-agents-list.md

用于对 `codex-multi-agents` 的 agents 名单进行读取和维护。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-list.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-list.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](../../../test/codex-multi-agents/test_codex-multi-agents-list.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)

## [immutable]文件位置

- 脚本文件：[`skills/codex-multi-agents/scripts/codex-multi-agents-list`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-list.sh)
- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](../../../test/codex-multi-agents/test_codex-multi-agents-list.py)

## [immutable]参考

- 名单参考文件：[`agents-lists.md`](../../examples/scripts/codex-multi-agents-list/agents-lists.md)

## 参数约定

- `-file`：名单文件路径。
- `-status`：读取并展示名单信息（按列宽对齐输出）。
- `-find`：按姓名查询指定字段值。
- `-replace`：修改指定人员的字段值。
- `-add`：新增人员。
- `-delete`：删除人员。
- `-init`：按人员配置向对应 `tmux` 会话发送初始化消息。
- `-name`：人员姓名（用于定位目标行）。
- `-key`：待查询/修改字段名。
- `-value`：待写入字段值。
- `-type`：新增人员时写入启动类型（如 `codex`、`claude`）。

## 字段约束

- `姓名` 为不可修改字段，不允许通过 `-replace` 修改。
- `姓名` 在名单文件中必须唯一。
- `-key` 的值必须与名单表头字段名一致。
- 表头必须包含基础字段：`姓名`、`状态`、`会话`、`agent session`、`介绍`、`提示词`、`归档文件`。
- 启动字段支持两种列名：`启动设置` 或 `启动类型`。
- `worktree` 为可选列；若存在则参与 `-add` 生成与 `-init` 读取。

## 并发约束

- 写操作（`-replace`、`-add`、`-delete`）使用 `flock` 文件锁，避免并发写入冲突。
- 非写文件操作（`-status`、`-find`、`-init`）不加锁，仅进行读取、解析或外部会话调用。
- 锁对象为目标名单文件本身，不创建 `<file>.lock` 等额外锁文件。

## 功能

### 读取 agents 名单

命令：

```bash
codex-multi-agents-list.sh -file "agents-lists.md" -status
```

功能说明：

- 读取 `-file` 指定的名单文件。
- 输出表头和非全空数据行。
- 读取阶段统计各列最大显示宽度，输出时按宽度对齐。

注意事项：

- `-file` 路径必须存在且可读。
- 名单文件需符合参考结构。
- 建议使用 UTF-8 编码保存名单文件。

### 查询字段

命令：

```bash
codex-multi-agents-list.sh -find -file "agents-lists.md" -name "xiaoming" -key "归档文件"
```

功能说明：

- 根据人员 `name` 查询指定字段 `key` 的值。
- 标准输出仅返回字段值（单行）。

注意事项：

- `-find` 为只读操作，不加锁。

### 修改字段

命令：

```bash
codex-multi-agents-list.sh -replace -file "agents-lists.md" -name "xiaoming" -key "归档文件" -value "aaa"
```

功能说明：

- 根据人员 `name` 修改指定字段 `key` 的值。

注意事项：

- 关键字 `姓名` 不可修改。
- 修改时使用 `flock` 加锁，避免并发写入冲突。

### 添加人员

命令：

```bash
codex-multi-agents-list.sh -add -file "agents-lists.md" -name "liming" -type "codex"
```

功能说明：

- 新增人员行并写入 `姓名`、`启动设置/启动类型`。
- 自动生成不重复且仅包含 ASCII 字符的 `会话`、`agent session` 值。
- 若表头包含 `worktree` 列，则自动生成 `worktree` 值。
- 默认生成规则分别为 `sess-<随机串>`、`agent-<随机串>`，`worktree` 列存在时使用 `wt-<随机串>`。
- 仅更新名单文件，不负责创建 tmux 会话或启动客户端。

注意事项：

- 不允许添加同名人员。
- 写入前使用 `flock` 加锁，避免并发冲突。

### 删除人员

命令：

```bash
codex-multi-agents-list.sh -delete -file "agents-lists.md" -name "xiaoming"
```

功能说明：

- 根据人员 `name` 删除对应行。

注意事项：

- 删除前使用 `flock` 加锁，避免并发冲突。

### 初始化人员

命令：

```bash
codex-multi-agents-list.sh -init -file "agents-lists.md" -name "xiaoming"
```

功能说明：
- 根据 `-name` 定位目标行，读取 `会话`、`提示词`、`归档文件`、`职责` 字段；若存在 `worktree` 列则读取其值。
- 发送文本格式固定为：`你的名字叫做<name>，从现在起只需要严格按照<提示词>进行工作以及"AGENTS.md"进行工作,你的专属文件夹在<归档文件>，你的职责是<职责>。请仔细阅读<提示词>，确保更新信息同步`。
- [immutable]使用 `tmux send-keys -t <会话> "<formatted_message>"` 下发初始化消息。等待一秒后，使用 `tmux send-keys -t <session-id> ENTER` 确保消息被收到。

注意事项：

- `-init` 不修改名单文件内容，不参与文件写锁竞争。
- 目标 `会话` 不能为空；若会话不存在，返回 `RC=3`。
- 若运行环境缺少 `tmux`，返回 `RC=2`。
- `职责` 列为可选列；若不存在或为空，消息中的职责部分按空值处理。



### 压缩人员上下文

命令：

```bash
codex-multi-agents-list.sh -compact -file "agents-lists.md" -name "xiaoming"
```

功能说明：
- 根据 `-name` 定位目标行，读取 `会话`、`提示词`、`归档文件`、`职责` 字段；若存在 `worktree` 列则读取其值。
- [immutable]使用 `tmux send-keys -t <会话> "/compact"` 下发压缩命令消息。等待一秒后，使用 `tmux send-keys -t <session-id> ENTER` 确保消息被收到。等待三秒后使用 `tmux send-keys -t <会话> "你的名字叫做<name>，从现在起只需要严格按照<提示词>进行工作以及"AGENTS.md"进行工作，当你压缩完成后，回报管理员。"` 下发回报消息。等待一秒后，使用 `tmux send-keys -t <session-id> ENTER` 确保消息被收到。

注意事项：
- 目标 `会话` 不能为空；若会话不存在，返回 `RC=3`。
- 若运行环境缺少 `tmux`，返回 `RC=2`。
- `职责` 列为可选列；若不存在或为空，消息中的职责部分按空值处理。

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
- 含义：文件错误（`-file` 不存在、不可读、格式不合法）。
- 输出：在标准错误（stderr）中打印文件路径和失败原因。

- 返回码：`3`
- 含义：数据错误（目标人员不存在、人员重名、字段名非法）。
- 输出：在标准错误（stderr）中打印具体数据校验失败原因。

- 返回码：`4`
- 含义：并发或锁错误（文件加锁失败、锁超时、锁冲突）。
- 输出：在标准错误（stderr）中打印锁状态与处理建议。

- 返回码：`5`
- 含义：未分类内部错误（脚本执行异常）。
- 输出：在标准错误（stderr）中打印错误摘要。

## 测试

- 测试文件位置：[`test/codex-multi-agents/test_codex-multi-agents-list.py`](../../../test/codex-multi-agents/test_codex-multi-agents-list.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-list.py`

### 测试目标

- 验证脚本 7 个核心功能：读取、查询、添加、修改、删除、初始化、压缩上下文。
- 验证返回码约定：`0/1/2/3/4/5` 行为与文档一致。
- 验证字段约束：`姓名` 不可改、`姓名` 唯一、字段名合法。
- 验证并发行为：写锁冲突时返回 `RC=4`。
- 验证 `-compact` 场景下的 tmux 压缩命令发送、回报消息发送与缺失会话错误处理。

### 测试范围

- 命令行参数解析与参数组合校验。
- Markdown 表格结构解析与数据完整性校验。
- 文件读写与原子更新。
- 并发锁（`flock`）处理。
- 写操作对目标名单文件本体的加锁行为。
- `-init` 场景下的 tmux 会话校验与消息发送行为。
- `-compact` 场景下的 tmux 会话校验、压缩命令发送与后续回报消息发送行为。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TC-001 | `-status` | 正常读取名单 | 合法名单文件存在 | `-file <path> -status` | 返回码 `0`；输出包含表头与人员数据 |
| TC-002 | `-find` | 查询字段成功 | 名单存在目标人员和字段 | `-file <path> -find -name 小明 -key 归档文件` | 返回码 `0`；stdout 输出字段值 |
| TC-003 | `-find` | 查询不存在人员 | 名单不存在目标姓名 | `-file <path> -find -name 不存在 -key 归档文件` | 返回码 `3`；报错 `agent not found` |
| TC-004 | `-add` | 新增人员成功 | 名单中不存在目标姓名 | `-file <path> -add -name 王五 -type codex` | 返回码 `0`；文件新增人员并生成会话字段 |
| TC-005 | `-add` | 新增同名人员 | 名单中已存在 `小明` | `-file <path> -add -name 小明 -type codex` | 返回码 `3`；报错 `agent already exists` |
| TC-006 | `-replace` | 修改字段成功 | 名单中存在 `小明` 且字段 `状态` 存在 | `-file <path> -replace -name 小明 -key 状态 -value ready` | 返回码 `0`；字段被更新 |
| TC-007 | `-replace` | 修改不可变字段 `姓名` | 名单中存在目标人员 | `-file <path> -replace -name 小明 -key 姓名 -value 新名字` | 返回码 `3`；报错 `immutable` |
| TC-008 | `-replace` | 修改非法字段 | 名单中不存在该字段名 | `-file <path> -replace -name 小明 -key 不存在字段 -value x` | 返回码 `3`；报错 `invalid field name` |
| TC-009 | `-delete` | 删除人员成功 | 名单中存在 `李白` | `-file <path> -delete -name 李白` | 返回码 `0`；文件中不再包含 `李白` |
| TC-010 | `-delete` | 删除不存在人员 | 名单中不存在目标姓名 | `-file <path> -delete -name 不存在` | 返回码 `3`；报错 `agent not found` |
| TC-011 | 参数校验 | 缺少必填参数 | 合法名单文件存在 | `-file <path> -replace -name 小明 -key 状态` | 返回码 `1`；报错缺少 `-value` |
| TC-012 | 文件校验 | 文件不存在 | 指定路径不存在 | `-file <missing> -status` | 返回码 `2`；报错 `file not found` |
| TC-013 | 表结构校验 | 表头缺少 `姓名` 列 | 文件为非法表头 | `-file <path> -status` | 返回码 `2`；报错缺少 `姓名` 列 |
| TC-014 | 数据校验 | 名单内 `姓名` 重复 | 文件中存在重复姓名 | `-file <path> -status` | 返回码 `3`；报错 `duplicate 姓名` |
| TC-015 | 并发锁 | 写锁冲突 | 另一个进程已持有目标名单文件锁 | `-file <path> -add -name 并发测试 -type codex` | 返回码 `4`；报错 `cannot acquire lock` |
| TC-016 | `-replace` | 支持空值写入 | 名单中存在目标人员 | `-file <path> -replace -name 小明 -key 状态 -value ""` | 返回码 `0`；字段被清空 |
| TC-017 | `-status` | 锁冲突时仍可读 | 目标名单文件被占用 | `-file <path> -status` | 返回码 `0`；正常输出 |
| TC-018 | 兼容性 | 历史行缺少新增尾列 | 行列数少于表头 | `-file <path> -status` | 返回码 `0`；自动补空并可读取 |
| TC-019 | `-init` | 初始化消息发送成功 | 名单存在目标人员；`tmux` 会话存在 | `-file <path> -init -name 小明` | 返回码 `0`；执行 `tmux send-keys`；stdout 包含 `OK: init 小明` |
| TC-020 | `-init` | 初始化时目标会话不存在 | 名单存在目标人员；会话不存在 | `-file <path> -init -name 小明` | 返回码 `3`；stderr 包含 `target session not found` |
| TC-021 | `-compact` | 压缩命令与回报消息发送成功 | 名单存在目标人员；`tmux` 会话存在 | `-file <path> -compact -name 小明` | 返回码 `0`；先发送 `/compact`，再发送回报管理员消息，stdout 包含 `OK: compact 小明` |
| TC-022 | `-compact` | 压缩时目标会话不存在 | 名单存在目标人员；会话不存在 | `-file <path> -compact -name 小明` | 返回码 `3`；stderr 包含 `target session not found` |

### 通过准则

- 所有用例执行完成，且返回码与预期一致。
- 文件内容变更类用例（新增/修改/删除）均验证到实际文件状态。
- 错误路径用例在 `stderr` 输出可识别错误信息。

### 用例与自动化映射

- TC-001 -> `test_status_outputs_table_and_returns_0`
- TC-002 -> `test_find_field_success`
- TC-003 -> `test_find_missing_agent_returns_rc3`
- TC-004 -> `test_add_agent_success`
- TC-005 -> `test_add_duplicate_agent_returns_rc3`
- TC-006 -> `test_replace_field_success`
- TC-007 -> `test_replace_name_field_is_immutable`
- TC-008 -> `test_replace_unknown_field_returns_rc3`
- TC-009 -> `test_delete_agent_success`
- TC-010 -> `test_delete_missing_agent_returns_rc3`
- TC-011 -> `test_argument_error_returns_rc1`
- TC-012 -> `test_file_not_found_returns_rc2`
- TC-013 -> `test_invalid_table_missing_name_column_returns_rc2`
- TC-014 -> `test_duplicate_name_in_file_returns_rc3`
- TC-015 -> `test_lock_conflict_returns_rc4`
- TC-016 -> `test_replace_supports_empty_value`
- TC-017 -> `test_status_ignores_lock_and_returns_rc0`
- TC-018 -> `test_status_accepts_rows_missing_new_tail_column`
- TC-019 -> `test_init_agent_sends_message_success`
- TC-020 -> `test_init_agent_missing_session_returns_rc3`
- TC-021 -> `test_compact_agent_sends_compact_and_report`
- TC-022 -> `test_compact_agent_missing_session_returns_rc3`
