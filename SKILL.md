---
name: codex-multi-agents
description: 基于 tmux 的多会话协作框架。
---

# codex-multi-agents

## 文档信息
- 创建者：`榕`
- 最后一次更改：`榕`

## 约定
- 如无特别说明，`agents/` 位于项目根目录。
- 文档中的相对路径默认以当前 skill 目录（`skills/codex-multi-agents/`）为基准。
- 文档内路径及生成文件路径统一使用相对路径，避免泄露用户本机路径；仅在脚本传参时使用绝对路径。

## 快速跳转
- [适用场景](#适用场景)
- [强制约束](#强制约束)
- [执行入口](#执行入口)
- [角色交互](#角色交互)
- [目录](#目录)
- [流程](#流程)
- [初始化](#初始化)
- [启动](#启动)
- [新增角色](#新增角色)
- [更新角色](#更新角色)
- [终止](#终止)
- [默认提示词](#默认提示词)
- [输出与审计](#输出与审计)
- [参考](#参考)

## 适用场景
- 用户希望将任务拆分给多个角色并行或轮转执行。
- 需要严格隔离角色上下文。
- 需要完整日志，能够追踪每个角色的操作历史。

## 强制约束
- 必须遵守仓库中的 `AGENTS.md` 规则。
- 所有角色不得直接修改 `config`、`TODO.md`、`DONE.md`、`agents-lists.md` 以及其他角色归档文件。
- 任务状态变更（如完成、暂停）必须通过脚本执行，不可手工改表。
- 角色新增、状态变更必须回写到 agents 名单中。
- 所有角色运行与交互必须可追踪（消息、日志、归档路径可定位）。
- 除明确说明外，不要跳过初始化和配置校验步骤。
- 同一个角色同时只能进行一项任务。
- 只有管理员可以分配任务。其他人员不可以进行任务分配。
- 任务完成后必须用脚本向管理员回报。
- 涉及工作树的任务必须使用 `git worktree` 新建工作树进行，不要在 `main` 分支直接创建文件夹或改动。
- 实现任务需包含测试验证，默认不拆分独立 test 任务。

## 执行入口
- 名单维护脚本：[`./scripts/codex-multi-agents-list.sh`](./scripts/codex-multi-agents-list.sh)
- 会话通信脚本：[`./scripts/codex-multi-agents-tmux.sh`](./scripts/codex-multi-agents-tmux.sh)
- 任务调度脚本：[`./scripts/codex-multi-agents-task.sh`](./scripts/codex-multi-agents-task.sh)
- 规范文档目录：[`../../spec/codex-multi-agents/scripts/`](../../spec/codex-multi-agents/scripts/)

## 角色交互
- 管理员（`ROOT_NAME`）负责分发任务与协调角色。
- 角色间沟通统一通过 `codex-multi-agents-tmux.sh -talk` 执行。
- 发送消息时必须明确接收对象、目标会话和日志路径（`-log`）。
- 普通角色完成任务后，需向管理员会话回报完成情况、后续计划和任务日志路径。
- 任务分发应明确输入与输出：输入为任务清单与名单，输出为已分发任务与对话日志。

## 目录
- 日志目录：`agents/codex-multi-agents/log`
- 临时目录：`agents/codex-multi-agents/tmp`
- 配置文件：`agents/codex-multi-agents/config/config.txt`
- 名单文件：`agents/codex-multi-agents/agents-lists.md`
- 交互日志：`agents/codex-multi-agents/log/talk.log`
- 示例目录：`./examples/`

## 流程
### 初始化
- 若配置文件不存在，则创建 `agents/codex-multi-agents/config/config.txt`。
- 配置内容至少包含：`ROOT_NAME`、`TODO_FILE`、`AGENTS_FILE`、`LOG_DIR`、`TMP_DIR`。
- 向用户确认管理员名称，写入 `ROOT_NAME`。
- 向用户确认 `TODO_FILE` 路径并写入配置；若文件不存在则创建。
- 新增管理员 agent；新增角色步骤参考：[新增角色](#新增角色)。

### 启动
- 读取配置文件和 agents 名单。
- 若配置不存在，回到 [初始化](#初始化)。
- 使用 `codex-multi-agents-tmux.sh -talk` 向管理员下达开始任务信息。
- 实现任务完成后需同步测试结果与日志路径。
- 审查不通过则回到实现任务（含测试）再次迭代，直到审查通过。
- 测试未达标时必须补齐测试结果后再进入审查。

### 新增角色
- 与用户确认角色名称 `<name>`。
- 与用户确认角色类型 `<type>`（如 `codex`、`claude`）。
- 与用户确认角色工作树；如未指定，默认使用项目路径。
- 若 `<type>` 为 `claude`，需提前告知用户初始化流程可能不支持或需手动处理。
- 执行新增命令（`-file` 使用绝对路径）：

```bash
./scripts/codex-multi-agents-list.sh -add \
  -file <repo_abs_path>/agents/codex-multi-agents/agents-lists.md \
  -name <name> \
  -type <type>
```

- 创建归档目录：`agents/codex-multi-agents/agents/<name>/`。
- 创建提示词文件：`agents/codex-multi-agents/agents/<name>/<name>.prompt.md`。
- 从名单中读取并确认字段：`会话`、`agent session`、`提示词`、`职责`、`归档文件`。
- 初始化会话环境：

```bash
./scripts/codex-multi-agents-tmux.sh -init-env -file <AGENTS_LIST_ABS_PATH> -name <name>
```

- 向新角色下发基础信息：

```bash
./scripts/codex-multi-agents-list.sh -init -file <AGENTS_LIST_ABS_PATH> -name <name>
```

### 更新角色
- 当用户修改角色提示词后，使用 `-init` 重新向该角色同步基础信息。

```bash
./scripts/codex-multi-agents-list.sh -init -file <AGENTS_LIST_ABS_PATH> -name <name>
```

### 终止
- 使用 `codex-multi-agents-tmux.sh -talk` 向管理员下达终止信息。

## 默认提示词
- 管理员提示词：[`./examples/prompt-root.md`](./examples/prompt-root.md)
- 普通角色提示词：[`./examples/prompt.md`](./examples/prompt.md)

## 输出与审计
- 每次角色创建或消息下发后，应记录操作结果（成功/失败、原因、关联路径）。
- 关键审计对象包括：
  - 名单文件：`agents/codex-multi-agents/agents-lists.md`
  - 对话日志：`agents/codex-multi-agents/log/`
  - 角色归档：`agents/codex-multi-agents/agents/<name>/`

## 参考
- 名单脚本：[`./scripts/codex-multi-agents-list.sh`](./scripts/codex-multi-agents-list.sh)
- tmux 脚本：[`./scripts/codex-multi-agents-tmux.sh`](./scripts/codex-multi-agents-tmux.sh)
- 任务脚本：[`./scripts/codex-multi-agents-task.sh`](./scripts/codex-multi-agents-task.sh)
- 规范文档：[`../../spec/codex-multi-agents/scripts/`](../../spec/codex-multi-agents/scripts/)
