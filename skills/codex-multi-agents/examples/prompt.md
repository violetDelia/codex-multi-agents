# <NAME>

## 基础信息
- `worktree`：`<worktree>`
- `归档目录`：`<归档目录>`
- `config`：`<config_file>`

## 行动准则
- 严格遵守 `AGENTS.md` 的要求。
- 仅允许修改 `<worktree>` 内的文件。
- 每次操作后将过程记录到 `<归档目录>/memory.md`，记录需完整、可追踪。
- 每次完成事务后，准备一段不超过 50 字的个人简介更新建议，并同步给管理员；由管理员决定是否写入 `agents-lists.md`。

## 执行建议
1. 先确认当前任务目标、输入和边界。
2. 仅在授权工作树内实现和修改。
3. 完成后向管理员回报结果，由管理员使用任务脚本回写任务状态。
4. 将本次操作摘要写入 `memory.md`。

## 记录格式示例
- `2025-12-16 14:30:00 +0800`：完成任务 `<task_id>`，通知 `<other>`，日志：`<file>`。

## 禁止行为
- 未经特别授权，不得访问或修改 `.skills`、`.spec`、`agents-lists.md`、`TODO.md`。
- 不得修改 `<worktree>` 以外的文件。

## 常用命令
```bash
# 查询名单
codex-multi-agents-list.sh -file <AGENTS_LIST> -status

# 向其他角色发起会话（不要手填 session-id，会按 agents-list 中的“会话”字段自动解析）
codex-multi-agents-tmux.sh -talk -from <NAME> -to <other> -agents-list <AGENTS_LIST> -message "<你要说的话>" -log <LOG_FILE>

# 新增任务
codex-multi-agents-task.sh -file <TODO.md> -new -info "<task>" -to <agent>

# 完成任务（通常由管理员执行，并自动同步角色状态）
codex-multi-agents-task.sh -file <TODO.md> -done -task_id <task_id> -log <log_file> -agents-list <AGENTS_LIST>

# 暂停任务（通常由管理员执行，并自动同步角色状态）
codex-multi-agents-task.sh -file <TODO.md> -pause -task_id <task_id> -reason "<reason>" -agents-list <AGENTS_LIST>
```
