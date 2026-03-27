# codex-multi-agents

本 README 只讲两件事：**怎么用**、**怎么跑示例**。

## 1) 5 分钟上手（可直接复制）

```bash
cd /home/lfr/codex-multi-agents

# 0. 准备示例文件
AGENTS_FILE="skills/codex-multi-agents/examples/agents-lists.md"
TODO_FILE="skills/codex-multi-agents/examples/TODO.md"

# 1. 查看当前人员列表
bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh \
  -file "$AGENTS_FILE" -status

# 2. 新建任务（会生成 task_id）
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file "$TODO_FILE" \
  -new -from 管理员 -to 小王 \
  -worktree /tmp/wt-demo \
  -log /tmp/task-demo.md \
  -info "实现 demo 并补测试"

# 3. 分发任务（把下面 task_id 替换成上一步输出）
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file "$TODO_FILE" \
  -dispatch -task_id T-20260328-xxxxxxx1 -to 小王 \
  -agents-list "$AGENTS_FILE" \
  -message "请开始处理，遇到阻塞及时反馈"

# 4. 执行完成后标记 done
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file "$TODO_FILE" \
  -done -task_id T-20260328-xxxxxxx1 \
  -log /tmp/task-demo.md \
  -agents-list "$AGENTS_FILE"

# 5. 查看看板状态
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file "$TODO_FILE" -status -task-list
```

## 2) 常用命令速查

### 2.1 人员管理：`codex-multi-agents-list.sh`

```bash
# 查看名单状态
bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh \
  -file skills/codex-multi-agents/examples/agents-lists.md -status

# 新增角色
bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh \
  -file skills/codex-multi-agents/examples/agents-lists.md \
  -add -name 新成员 -type codex

# 初始化角色环境（含提示词同步）
bash skills/codex-multi-agents/scripts/codex-multi-agents-list.sh \
  -file skills/codex-multi-agents/examples/agents-lists.md \
  -init -name 新成员
```

### 2.2 任务流转：`codex-multi-agents-task.sh`

```bash
# 新建任务
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file skills/codex-multi-agents/examples/TODO.md \
  -new -from 神秘人 -to 李白 \
  -worktree /home/lfr/kernelcode_generate/wt-demo \
  -log /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/13/demo.md \
  -info "实现 nn.xxx 并补测试"

# 分发（建议附带明确验收条件）
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file skills/codex-multi-agents/examples/TODO.md \
  -dispatch -task_id T-20260328-xxxxxxx2 -to 李白 \
  -agents-list skills/codex-multi-agents/examples/agents-lists.md \
  -message "验收: pytest -q test/operation/test_operation_nn.py -k xxx"

# 阻塞/恢复
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file skills/codex-multi-agents/examples/TODO.md \
  -pause -task_id T-20260328-xxxxxxx2 -info "worktree 不存在"

bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file skills/codex-multi-agents/examples/TODO.md \
  -continue -task_id T-20260328-xxxxxxx2

# 完成
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file skills/codex-multi-agents/examples/TODO.md \
  -done -task_id T-20260328-xxxxxxx2 \
  -log /tmp/demo-task.md \
  -agents-list skills/codex-multi-agents/examples/agents-lists.md
```

### 2.3 会话通信：`codex-multi-agents-tmux.sh`

```bash
# 初始化会话（首次）
bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh \
  -init-env -file skills/codex-multi-agents/examples/agents-lists.md -name 李白

# 发送消息
bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh \
  -talk -from 神秘人 -to 李白 \
  -agents-list skills/codex-multi-agents/examples/agents-lists.md \
  -message "请先检查任务日志，再开始实现" \
  -log /tmp/talk.log
```

## 3) 推荐工作流模板

```text
spec 任务 -> 实现任务 -> 审查/复审任务 -> 合并任务 -> 同步确认任务
```

每次分发建议固定写清：
- `worktree` 路径（并先确认已创建）
- 验收命令（例如 `pytest -q ...`）
- 阻塞时必须 `-pause` 并主动询问

## 4) 常见报错与处理

```text
target session not found
```
先执行 `tmux` 初始化：
```bash
bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -init-env -file <agents-file> -name <agent>
```

```text
worktree not found
```
先创建或修正路径，再分发任务。

```text
task already exists in running list
```
任务已在执行中，避免重复 `-dispatch`。

## 5) 更多示例

- `EXTENSIONS.md`（扩展说明：分工、分发、阻塞、合并、同步策略）
- `skills/codex-multi-agents/examples/commands-quickstart.md`
- `skills/codex-multi-agents/examples/common-guides.md`
- `skills/codex-multi-agents/SKILL.md`
