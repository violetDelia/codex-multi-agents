# codex-multi-agents-task.md

## 功能简介

定义 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh` 的任务调度行为，覆盖任务分发、完成、暂停、继续、改派、新建与状态查询，并约束 `TODO.md`/`DONE.md`、`agents-lists.md` 以及分发消息发送、分发前角色信息初始化链路的协同更新规则。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`神秘人`
- `spec`：[`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](../../../spec/codex-multi-agents/scripts/codex-multi-agents-task.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](../../../skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)

## 依赖

- `TODO.md`：任务数据源。
- `DONE.md`：完成任务归档文件（与 `TODO.md` 同级目录）。
- `agents/codex-multi-agents/agents-lists.md`：角色状态源文件。
- `skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`：用于读取目标角色 `会话` 字段。
- `skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`：用于在分发后可选发送任务消息。
- `agents/codex-multi-agents/config/config.txt`：可选提供 `ROOT_NAME` 与 `LOG_DIR`。
- `flock`：用于写操作锁定。

## 目标

- 提供统一的任务分发、完成、暂停、继续、改派、新建与状态查询命令。
- 维护 `TODO.md` 与 `DONE.md` 的一致性与可追踪性。
- 在分发、完成、暂停、继续时同步维护 `agents-lists.md` 的角色状态。
- 在 `-dispatch` 提供 `-message` 时，自动向目标角色 tmux 会话发送任务消息。
- 在每次 `-dispatch` 执行前，固定调用一次 `codex-multi-agents-list.sh -init`，更新目标角色信息并提醒其同步自身提示词信息。
- 在缺参、缺文件、坏数据或锁冲突时给出明确返回码。

## 限制与边界

- `TODO.md`、`DONE.md` 与 `agents-lists.md` 的表格更新必须局限于对应任务/角色记录，不得改写无关段落。
- 一次命令只能执行一个主操作：`-dispatch/-done/-pause/-continue/-reassign/-new/-status` 七选一。
- `-dispatch/-done/-pause/-continue/-reassign` 必须提供 `-agents-list <path>`，用于同步角色状态。
- `-reassign` 仅适用于 `正在执行的任务` 表中的任务；任务列表中的任务不可改派。
- `-dispatch` 可选提供 `-message <text>`；提供后会在分发提交成功后继续发送一条对话消息。
- `TODO.md` 必须包含段落：
  - `## 正在执行的任务`
  - `## 任务列表`
  - 可选 `## 需要用户确认的事项`
- `正在执行的任务` 表头：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |`
- `任务列表` 表头：
  - `| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |`
- `需要用户确认的事项` 表头：
  - `| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |`
- `任务 ID` 在 `正在执行的任务` 与 `任务列表` 中必须唯一。
- `DONE.md` 位于 `TODO.md` 同级目录；若不存在需自动创建，默认表头：
  - `| 任务 ID | 描述 | 指派 | 完成状态 | 完成时间 | 日志文件 | 备注 |`
- `完成状态` 固定写入 `已完成`。
- `创建时间`/`完成时间` 推荐格式：`YYYY-MM-DD HH:MM:SS ±HHMM`。
- `agents-lists.md` 中角色状态当前仅使用 `busy` / `free` 两个值。
- 角色状态同步规则：
  - `-dispatch` 成功后，将目标角色状态更新为 `busy`。
  - `-done` / `-pause` 成功后，若该角色已无其他 `状态=进行中` 的任务，则更新为 `free`。
  - `-done` / `-pause` 若该角色仍有其他 `状态=进行中` 的任务，则保持 `busy`。
  - `-continue` 成功后，若任务存在指派角色，则将该角色状态更新为 `busy`。
  - `-reassign` 成功后，需同时重算旧指派与新指派的角色状态：旧指派若已无其他 `状态=进行中` 任务则置 `free`，新指派若存在 `状态=进行中` 任务则置 `busy`。
- 分发消息规则：
  - `-dispatch` 时，先尽力执行一次 `codex-multi-agents-list.sh -init`，再提交 `TODO.md`/`agents-lists.md` 更新。
  - `-dispatch -message <text>` 时，提交 `TODO.md`/`agents-lists.md` 更新后，再调用 `codex-multi-agents-tmux.sh -talk`。
  - `-from` 固定取 `config.txt` 的 `ROOT_NAME`；若配置缺失，则回退为 `scheduler`。
  - `codex-multi-agents-tmux.sh -talk` 使用 `-agents-list`，由脚本内部按目标角色 `-to` 自动解析 `会话` 列。
  - `-log` 固定取 `config.txt` 的 `LOG_DIR/talk.log`；若配置缺失，则回退为 `$(dirname agents-lists.md)/log/talk.log`。
  - 若消息发送失败，不回滚已提交的分发结果；命令返回消息发送链路的错误码，并提示只需补发 `codex-multi-agents-tmux.sh -talk`。
- 分发前角色信息初始化规则：
  - 每次执行 `-dispatch` 前，必须调用一次 `codex-multi-agents-list.sh -init -file <agents-lists.md> -name <指派>`。
  - 初始化用于更新目标角色信息，并提示角色重新同步 `提示词`、`AGENTS.md` 与自身职责信息。
  - 初始化为尽力而为链路；若执行失败，仅输出告警，不阻塞后续分发，也不改变命令成功/失败语义。
- 并发约束：
  - `-dispatch/-done/-pause/-continue/-reassign/-new` 必须使用 `flock` 锁定目标文件。
  - `-dispatch/-pause/-continue/-reassign` 同时写 `TODO.md` 与 `agents-lists.md` 时，锁顺序固定为先 `TODO.md` 后 `agents-lists.md`。
  - `-done` 同时写 `TODO.md`、`DONE.md` 与 `agents-lists.md` 时，锁顺序固定为先 `TODO.md` 后 `DONE.md` 再 `agents-lists.md`。
  - `-status` 只读，不加锁。
- 返回码约定：
  - `0` 成功。
  - `1` 参数错误。
  - `2` 文件错误。
  - `3` 数据错误（任务不存在、ID 冲突、表头非法）。
  - `4` 锁冲突或并发错误。
  - `5` 内部错误。

## 公开接口

### `codex-multi-agents-task.sh`

功能说明：

- 统一处理任务调度与查询命令。

参数说明：

- `-file <path>`：`TODO.md` 文件路径（必填）。
- `-agents-list <path>`：`agents-lists.md` 文件路径；`-dispatch/-done/-pause/-continue/-reassign` 时必填。
- `-message <text>`：仅 `-dispatch` 可用；提供后自动向目标角色发送任务消息。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -status -doing
```

注意事项：

- `-file` 必须存在且结构合法。

返回与限制：

- 返回码遵循“限制与边界”约定。

#### `-status`

功能说明：

- 输出任务状态表（正在执行或任务列表）。

参数说明：

- `-status`：查看任务状态。
- `-doing`：输出正在执行任务表。
- `-task-list`：输出任务列表表。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -status -doing
```

注意事项：

- `-doing` 与 `-task-list` 必须且只能二选一。

返回与限制：

- 成功返回 `0`，参数组合错误返回 `1`。

#### `-dispatch`

功能说明：

- 从任务列表分发任务至正在执行区。

参数说明：

- `-dispatch`：执行分发操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-to <name>`：指派对象（必填）。
- `-agents-list <path>`：角色名单文件（必填）。
- `-message <text>`：分发后自动发送给目标角色的消息正文（可选）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -dispatch -task_id "EX-3" -to "worker-a" -agents-list "./agents/codex-multi-agents/agents-lists.md" -message "请处理任务 EX-3，完成后回报。"
```

注意事项：

- 若任务不在任务列表中，返回 `3`。
- 若 `worktree` 为空，保持空值。
- 迁移后写入 `状态=进行中`，`用户指导` 保持空列。
- 分发前会先执行一次 `codex-multi-agents-list.sh -init`，更新目标角色信息并提醒其同步自身信息。
- 成功后需同步将目标角色状态更新为 `busy`。
- 若提供 `-message`，成功分发后还需调用 `codex-multi-agents-tmux.sh -talk -agents-list <agents-lists.md>`，由对话脚本自动解析目标角色会话。
- 若消息发送失败，分发结果保持已提交，不回滚 `TODO.md` 与 `agents-lists.md`。
- 若分发前初始化失败，仅输出警告，不影响分发结果。

返回与限制：

- 成功返回 `0`；任务不存在或冲突返回 `3`。

#### `-done`

功能说明：

- 完成任务并写入 `DONE.md`。

参数说明：

- `-done`：执行完成操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-log <path>`：日志文件路径（必填，写入记录）。
- `-agents-list <path>`：角色名单文件（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -done -task_id "EX-1" -log "./log/record.md" -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- 任务不存在返回 `3`。
- `-log` 仅写入记录字段，不校验文件存在性。
- 完成后需检查该角色是否仍有其他 `进行中` 任务；若无，则将角色状态更新为 `free`。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

#### `-pause`

功能说明：

- 暂停正在执行的任务。

参数说明：

- `-pause`：执行暂停操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-agents-list <path>`：角色名单文件（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -pause -task_id "EX-2" -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- 任务不存在返回 `3`。
- 暂停后需检查该角色是否仍有其他 `进行中` 任务；若无，则将角色状态更新为 `free`。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

#### `-continue`

功能说明：

- 继续已暂停任务，将其状态恢复为 `进行中`。

参数说明：

- `-continue`：执行继续操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-agents-list <path>`：角色名单文件（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -continue -task_id "EX-2" -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- 任务不存在返回 `3`。
- 仅允许继续 `状态=暂停` 的任务；否则返回 `3`。
- 继续成功后，若任务存在指派角色，需同步角色状态为 `busy`。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

#### `-reassign`

功能说明：

- 重新指派正在执行中的任务，更新任务记录与角色状态。

参数说明：

- `-reassign`：执行改派操作。
- `-task_id <id>`：目标任务 ID（必填）。
- `-to <name>`：新的指派对象（必填）。
- `-agents-list <path>`：角色名单文件（必填）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -reassign -task_id "EX-2" -to "worker-c" -agents-list "./agents/codex-multi-agents/agents-lists.md"
```

注意事项：

- 任务不存在返回 `3`。
- 新指派角色必须存在于 `agents-lists.md`；否则返回 `3`。
- 改派后需重算旧/新指派角色状态。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

#### `-new`

功能说明：

- 新建任务并写入任务列表。

参数说明：

- `-new`：执行新建操作。
- `-info <desc>`：任务描述（必填）。
- `-to <name>`：指派对象（可选）。
- `-from <name>`：发起人（可选）。
- `-worktree <path>`：工作树（可选）。
- `-log <path>`：记录文件（可选，写入“记录文件”列）。

使用示例：

```bash
codex-multi-agents-task.sh -file "./skills/codex-multi-agents/examples/TODO.md" -new -info "补充单元测试" -to "worker-b"
```

注意事项：

- 任务 ID 按“日期-hash”规则生成，推荐格式 `T-YYYYMMDD-<8位hash>`。

返回与限制：

- 成功返回 `0`；失败返回对应错误码。

## 测试

- 测试文件：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](../../../test/codex-multi-agents/test_codex-multi-agents-task.py)
- 执行命令：`pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`
- 覆盖率命令：`pytest -q --cov=skills/codex-multi-agents/scripts/codex-multi-agents-task.sh --cov-branch --cov-report=term-missing test/codex-multi-agents/test_codex-multi-agents-task.py`
- 当前覆盖率信息：`N/A`（shell 脚本由子进程执行，`pytest-cov` 会报告 `no-data-collected`；按规则豁免 `95%` 覆盖率达标线，以 `TC-001..025` 用例覆盖为当前基线）

### 测试目标

- 验证任务分发、完成、暂停、继续、改派、新建与状态查询。
- 验证 `TODO.md` 与 `DONE.md` 的跨文件流转。
- 验证 `agents-lists.md` 的角色状态会随 `-dispatch/-done/-pause/-continue/-reassign` 正确同步。
- 验证 `-dispatch -message` 会自动调用 tmux 对话脚本，并在失败时保留分发结果。
- 验证每次 `-dispatch` 前都会触发一次 `codex-multi-agents-list.sh -init` 链路。
- 验证返回码约定 `0/1/2/3/4/5`。
- 验证并发锁冲突返回 `RC=4`。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| TC-001 | `-dispatch` | 分发成功 | 任务位于任务列表 | `-file F -dispatch -task_id EX-3 -to worker-a -agents-list G` | 返回码 `0`；任务移入正在执行；状态=`进行中`；目标角色状态=`busy`；`创建时间`保持不变 |
| TC-002 | `-dispatch` | 任务不存在 | 任务列表不存在该 ID | `-file F -dispatch -task_id BAD -to worker-a` | 返回码 `3`；报错 task not found |
| TC-003 | `-done` | 完成成功 | 任务位于正在执行 | `-file F -done -task_id EX-1 -log L -agents-list G` | 返回码 `0`；TODO 移除任务；DONE 追加记录；若目标角色无其他进行中任务则状态=`free` |
| TC-004 | `-done` | 任务不存在 | 正在执行不存在该 ID | `-file F -done -task_id BAD -log L` | 返回码 `3`；报错 task not found |
| TC-005 | `-pause` | 暂停成功 | 任务位于正在执行 | `-file F -pause -task_id EX-2 -agents-list G` | 返回码 `0`；状态变为 `暂停`；若目标角色无其他进行中任务则状态=`free` |
| TC-006 | `-pause` | 任务不存在 | 正在执行不存在该 ID | `-file F -pause -task_id BAD` | 返回码 `3`；报错 task not found |
| TC-007 | `-new` | 新建成功（带指派） | TODO 结构合法 | `-file F -new -info "desc" -to worker-b` | 返回码 `0`；任务列表新增记录且指派=worker-b，`创建时间`写入成功 |
| TC-008 | `-new` | 新建成功（不带指派） | TODO 结构合法 | `-file F -new -info "desc"` | 返回码 `0`；任务列表新增记录且指派为空，`创建时间`写入成功 |
| TC-009 | 参数校验 | 缺少必填参数 | TODO 存在 | `-file F -done -task_id EX-1` | 返回码 `1`；报错缺少 `-log` |
| TC-010 | 文件校验 | TODO 文件不存在 | 路径不存在 | `-file missing -new -info "desc"` | 返回码 `2`；报错 file not found |
| TC-011 | 表结构校验 | 缺少任务段落或表头 | TODO 非法 | `-file F -new -info "desc"` | 返回码 `2`；报错 invalid table format |
| TC-012 | 并发锁 | 锁冲突 | 另一个进程持有 TODO 锁 | `-file F -dispatch -task_id EX-3 -to worker-a` | 返回码 `4`；报错 cannot acquire lock |
| TC-013 | `-status` | 输出正在执行任务 | TODO 结构合法 | `-file F -status -doing` | 返回码 `0`；输出包含运行中任务表 |
| TC-014 | `-status` | 输出任务列表 | TODO 结构合法 | `-file F -status -task-list` | 返回码 `0`；输出包含任务列表表 |
| TC-015 | `-status` | 参数组合错误 | TODO 结构合法 | `-file F -status` 或 `-file F -status -doing -task-list` | 返回码 `1`；报错 requires exactly one of -doing/-task-list |
| TC-016 | `-dispatch` | 分发后自动发消息成功 | 任务位于任务列表；目标角色存在会话；tmux 可用 | `-file F -dispatch -task_id EX-3 -to worker-a -agents-list G -message M` | 返回码 `0`；任务移入正在执行；角色状态=`busy`；调用 `tmux -talk` 并写入 `talk.log` |
| TC-017 | `-dispatch` | 分发成功但发消息失败 | 任务位于任务列表；目标角色会话不存在 | `-file F -dispatch -task_id EX-3 -to worker-a -agents-list G -message M` | 返回消息链路错误码；stderr 提示仅需补发消息；任务仍已移入正在执行且角色状态=`busy` |
| TC-018 | `-dispatch` | 分发前初始化成功 | 任务位于任务列表；目标角色会话存在 | `-file F -dispatch -task_id EX-3 -to worker-a -agents-list G` | 返回码 `0`；先调用 `list -init`；再完成任务分发；角色状态=`busy` |
| TC-019 | `-continue` | 继续成功 | 任务位于正在执行且状态=`暂停` | `-file F -continue -task_id EX-2 -agents-list G` | 返回码 `0`；任务状态变为 `进行中`；目标角色状态=`busy` |
| TC-020 | `-continue` | 任务不存在 | 正在执行不存在该 ID | `-file F -continue -task_id BAD -agents-list G` | 返回码 `3`；报错 task not found |
| TC-021 | `-continue` | 状态不合法 | 任务存在但状态不是 `暂停` | `-file F -continue -task_id EX-2 -agents-list G` | 返回码 `3`；报错 task status is not paused |
| TC-022 | 参数校验 | 继续任务缺少角色名单参数 | TODO 存在 | `-file F -continue -task_id EX-2` | 返回码 `1`；报错缺少 `-agents-list` |
| TC-023 | `-reassign` | 改派成功 | 任务位于正在执行；新角色存在 | `-file F -reassign -task_id EX-2 -to worker-a -agents-list G` | 返回码 `0`；任务指派更新；旧/新角色状态按规则更新 |
| TC-024 | `-reassign` | 任务不存在 | 正在执行不存在该 ID | `-file F -reassign -task_id BAD -to worker-a -agents-list G` | 返回码 `3`；报错 task not found |
| TC-025 | 参数校验 | 改派缺少角色名单参数 | TODO 存在 | `-file F -reassign -task_id EX-2 -to worker-a` | 返回码 `1`；报错缺少 `-agents-list` |

### 用例与自动化映射

- TC-001 -> `test_dispatch_task_success`
- TC-002 -> `test_dispatch_missing_task_returns_rc3`
- TC-003 -> `test_done_task_moves_to_done_file_success`
- TC-004 -> `test_done_missing_task_returns_rc3`
- TC-005 -> `test_pause_task_success`
- TC-006 -> `test_pause_missing_task_returns_rc3`
- TC-007 -> `test_new_task_with_assignee_success`
- TC-008 -> `test_new_task_without_assignee_success`
- TC-009 -> `test_argument_error_returns_rc1`
- TC-010 -> `test_file_not_found_returns_rc2`
- TC-011 -> `test_invalid_todo_structure_returns_rc2`
- TC-012 -> `test_lock_conflict_returns_rc4`
- TC-013 -> `test_status_doing_outputs_running_table`
- TC-014 -> `test_status_task_list_outputs_list_table`
- TC-015 -> `test_status_requires_exactly_one_mode`
- TC-016 -> `test_dispatch_with_message_sends_talk_success`
- TC-017 -> `test_dispatch_with_message_failure_keeps_dispatch_result`
- TC-018 -> `test_dispatch_runs_init_before_dispatch`
- TC-019 -> `test_continue_task_success`
- TC-020 -> `test_continue_missing_task_returns_rc3`
- TC-021 -> `test_continue_requires_paused_status`
- TC-022 -> `test_continue_requires_agents_list`
- TC-023 -> `test_reassign_task_success`
- TC-024 -> `test_reassign_missing_task_returns_rc3`
- TC-025 -> `test_reassign_requires_agents_list`
