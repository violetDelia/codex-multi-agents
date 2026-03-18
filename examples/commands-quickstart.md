# codex-multi-agents 命令速查

以下内容为使用示例与参数速记，便于快速上手。更完整的行为细节以脚本与规范文档为准。

## 1. 名单管理（codex-multi-agents-list.sh）

脚本路径：`./scripts/codex-multi-agents-list.sh`

### 查看名单
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -status
```

### 查询字段
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -find -name 小明 -key 归档文件
```

### 新增人员
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -add -name 小王 -type codex
```

### 修改字段
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -replace -name 小明 -key 状态 -value busy
```

### 删除人员
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -delete -name 小王
```

### 初始化人员
```bash
bash ./scripts/codex-multi-agents-list.sh \
  -file agents/codex-multi-agents/agents-lists.md \
  -init -name 小明
```

参数速记：
- `-file` 名单文件路径
- `-name` 人员姓名
- `-type` 启动类型（示例：`codex`）
- `-key` 字段名
- `-value` 字段值

## 2. tmux 会话管理（codex-multi-agents-tmux.sh）

脚本路径：`./scripts/codex-multi-agents-tmux.sh`

### 发送对话并写日志
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -talk -from scheduler -to worker-a -session-id worker-a \
  -message "请处理任务 T1" \
  -log agents/codex-multi-agents/log/talk.log
```

### 按名单初始化角色环境
```bash
bash ./scripts/codex-multi-agents-tmux.sh \
  -init-env -file agents/codex-multi-agents/agents-lists.md -name 小明
```

参数速记：
- `-s` 会话名（仅 `-attach`）
- `-from/-to/-session-id/-message/-log` 对话参数（仅 `-talk`）
- `-file/-name` 名单参数（仅 `-init-env`）

## 3. 任务调度（codex-multi-agents-task.sh）

脚本路径：`./scripts/codex-multi-agents-task.sh`

### TODO 结构示例
```markdown
## 正在执行的任务
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 任务列表
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- |

## 需要用户确认的事项（可选）
| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |
| --- | --- | --- | --- | --- | --- |
```

### 新建任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -new -info "实现任务调度器告警" -to worker-b -from 李白 -worktree repo-x -log ./log/record-1.log
```

### 分发任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -dispatch -task_id T-20260308-xxxxxxx1 -to worker-a
```

### 暂停任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -pause -task_id T-20260308-xxxxxxx1
```

### 完成任务
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md \
  -done -task_id T-20260308-xxxxxxx1 \
  -log ./agents/codex-multi-agents/log/task-T-20260308-xxxxxxx1.log
```

### 查看状态
```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md -status -doing
```

```bash
bash ./scripts/codex-multi-agents-task.sh \
  -file ./TODO.md -status -task-list
```

参数速记：
- `-file` TODO 文件路径
- `-new/-dispatch/-pause/-done` 操作类型
- `-task_id` 任务 ID
- `-info` 任务描述
- `-to/-from/-worktree/-log` 可选任务字段
- `-status -doing/-task-list` 状态查询

## 4. 任务流转速记
- 实现任务默认包含测试验证。
- 审查不通过则回到实现任务（含测试）再次迭代，直到审查通过。

