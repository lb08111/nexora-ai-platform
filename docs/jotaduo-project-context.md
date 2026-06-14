# Jotaduo AIops 平台项目上下文交接文档

本文档用于新会话、新工作区或新机器接管项目时快速恢复上下文。新接手的 AI 助手应先阅读本文档，再阅读同目录下的技术方案、需求说明和部署文档。

## 项目定位

本项目基于开源项目 JotaDuo / JotaDuo Console 二次开发，目标是建设**支持至少 100 个用户和 100 个智能体**的企业级智能运维平台”Jotaduo AIops 平台”。

### 设计规模

- **用户规模**：至少 100 个并发用户，覆盖管理员和操作员两类角色。
- **智能体规模**：至少 100 个智能体，支持按需懒加载、空闲回收、LRU 淘汰。
- **存储要求**：所有业务数据必须使用 PostgreSQL 持久化，禁止生产环境使用 JSON 文件存储。
- **权限粒度**：三层权限模型（平台访问 → 智能体授权 → 能力审批），支持批量授权/撤销。
- **审计合规**：全链路审计日志（登录、API 操作、消息、工具调用、审批），满足金融行业合规要求。

所有功能设计和技术选型必须按照上述企业级规模目标来执行，不做玩具级实现。

### 核心目标

- 提供 Web 登录入口和用户体系。
- 建立用户、角色、菜单、智能体、工具、MCP、Skill 的权限治理。
- 将传统运维工具通过 CLI、API、MCP、Skill 等方式接入智能体，让 AI Agent 可受控地调度使用。
- 保留原开源项目已有能力，二开功能尽量独立，便于后续跟进上游更新。

## 代码与运行目录

本地源码目录：

```text
/app
```

当前 GitHub 仓库：

```text
git@github.com:lb08111/jotaduo-platform.git
```

上游仓库：

```text
https://github.com/agentscope-ai/QwenPaw.git
```

运行数据目录：

```text
/Users/leo/.jotaduo
/Users/leo/.jotaduo.secret
```

注意：`.jotaduo.secret` 包含认证、用户、权限、密钥类数据，不要提交到 GitHub。

## 常用启动与测试

启动本地服务：

```bash
cd /app
./start-jotaduo-zh.sh
```

默认访问：

```text
http://127.0.0.1:8088
```

认证状态：

- 当前已启用登录认证。
- 常用管理员：`admin`
- 当前测试密码：`123456`

二开模块测试：

```bash
cd /app
.venv/bin/python -m pytest -q tests/unit/jotaduo
```

最近一次验证结果：

```text
96 passed, 1 warning
```

## 已完成二开能力

### 品牌与中文化

- 登录页标题已调整为 `The future starts now`。
- 平台品牌改为“Jotaduo AIops 平台”。
- 替换了页面 Logo 和浏览器标题相关品牌信息。
- 左侧菜单已按平台规划重组。

### 用户与角色权限

已建设用户权限体系：

- 用户管理
- 角色管理
- 菜单权限
- API 权限
- 登录认证
- 退出登录

权限链路：

```text
用户 -> 角色 -> 菜单
```

用户数据文件：

```text
/Users/leo/.jotaduo.secret/auth.json
```

当前确认存在 11 个用户：

```text
zhangming
admin
huangmizhi
luyankun
wangshengquan
zouyumeng
luwenxing
zhangjiahe
liming
liuyang
admin
```

### 多租户智能体权限（2026-05-28 重构）

权限架构已从旧的「角色→智能体策略」简化为三层模型：

```text
第一层：平台访问 — 用户 + 角色 → 菜单 / 页面（保持不变）
第二层：智能体授权 — admin 创建智能体 → 授权给用户（agent_user_grants）
第三层：能力审批 — 按 5 类能力（skill/mcp/tool/acp/plugin）独立控制新增/删除审批开关
```

核心规则：
- admin 角色绕过所有授权检查，可看到全部智能体
- 普通用户只能看到和使用被授权的智能体
- 智能体在用户间共享（shared workspace 模式）
- 100 人企业规模，支持批量授权/撤销

数据文件：

```text
/Users/leo/.jotaduo.secret/jotaduo_agent_grants.json       # 智能体-用户授权
/Users/leo/.jotaduo.secret/jotaduo_capability_approval.json # 能力审批配置
/Users/leo/.jotaduo.secret/jotaduo_agent_templates.json     # 智能体模板
/Users/leo/.jotaduo.secret/jotaduo_governance.json          # 旧治理数据（resource_policies 保留）
```

核心代码：

```text
src/jotaduo_ext/jotaduo/authorization.py        # 授权判断（替代旧 governance 的 agent_policies）
src/jotaduo_ext/jotaduo/agent_grants.py          # 智能体-用户授权 CRUD
src/jotaduo_ext/jotaduo/capability_approval.py   # 能力审批配置
src/jotaduo_ext/jotaduo/agent_templates.py       # 智能体模板（4 内置 + 自定义）
src/jotaduo_ext/jotaduo/governance.py             # 旧治理（resource_policies 仍在用）
```

相关测试：

```text
tests/unit/jotaduo/test_authorization.py          # 13 cases
tests/unit/jotaduo/test_agent_grants.py           # 6 cases
tests/unit/jotaduo/test_capability_approval.py    # 7 cases
tests/unit/jotaduo/test_agent_templates.py        # 7 cases
tests/unit/jotaduo/test_governance.py             # 15 cases
```

API 端点：

```text
GET    /api/jotaduo/agent-grants/{agent_id}                 # 智能体已授权用户列表
GET    /api/jotaduo/agent-grants/user/{username}            # 用户已授权智能体列表
POST   /api/jotaduo/agent-grants/{agent_id}                 # 批量授权
DELETE /api/jotaduo/agent-grants/{agent_id}                 # 批量撤销
GET    /api/jotaduo/capability-approval-config              # 能力审批配置列表
PUT    /api/jotaduo/capability-approval-config/{type}       # 更新审批配置
GET    /api/jotaduo/agent-templates                         # 模板列表
POST   /api/jotaduo/agent-templates                         # 创建模板
GET    /api/jotaduo/agent-templates/{id}                    # 模板详情
PUT    /api/jotaduo/agent-templates/{id}                    # 更新模板
DELETE /api/jotaduo/agent-templates/{id}                    # 删除模板
```

初始化脚本：

```bash
.venv/bin/python scripts/init_multi_tenant.py
```

该脚本幂等执行：清空旧 agent_policies、初始化 5 类审批默认配置、初始化 4 个内置模板。

前端页面：

- 「智能体授权」页（/ops-governance）：三 Tab — 智能体授权（Transfer 穿梭框批量选人）、能力审批配置（5×3 Switch 矩阵）、智能体模板（CRUD）
- 「审批中心」页（/approval-center）：审批申请列表 + 审批规则配置 Tab（切换到新 API）

### 工具 / MCP / Skill 过滤

资源访问采用"后端统一过滤、前端直接展示"架构：

- 后端 `governance.py` 的 `agent_can_use_resource()` 负责判断智能体是否可用某资源。
- 默认放行规则：无策略或 `allowed_agents` 为空 = 所有智能体可用；只有显式配置了 `allowed_agents` 列表才做限制。
- 前端 `useSkills`/`useTools`/`useMCP` 直接使用后端 API 返回的数据，不再做客户端二次过滤。
- 运行时调用也会校验智能体是否拥有资源权限。

相关代码：

```text
src/jotaduo_ext/jotaduo/governance.py          # agent_can_use_resource / ensure_resource_access
src/jotaduo/app/routers/tools.py
src/jotaduo/app/routers/mcp.py
src/jotaduo/app/routers/skills.py
src/jotaduo/agents/react_agent.py
src/jotaduo/app/runner/runner.py
```

### 智能体级文件隔离

当前目标是做到智能体级隔离，不做用户级隔离。已补齐第一轮文件边界：

- `/api/files/preview/{filepath}` 现在会根据当前请求智能体解析 workspace，只允许预览当前智能体 workspace 内的文件。
- 内置 `read_file`、`write_file`、`edit_file`、`append_file` 工具现在要求目标路径落在当前智能体 workspace 内；相对路径仍按当前 workspace 解析。
- 跨智能体 workspace 或任意 workspace 外绝对路径会被拒绝。

相关代码：

```text
src/jotaduo/app/routers/files.py
src/jotaduo/agents/tools/file_io.py
```

相关测试：

```text
tests/unit/jotaduo/test_agent_workspace_file_isolation.py
```

### 审计日志

已建设日志审计能力，用于记录：

- 用户登录（含角色信息、失败原因）
- API 修改类操作（含 HTTP 方法、请求路径、查询参数、状态码）
- 页面访问（含页面标题）
- 聊天消息发送（含消息内容预览，最长 1000 字符）
- 智能体工具调用生命周期（含输入参数、执行结果、错误信息，最长 2000 字符）
- 权限拦截（含所需权限）
- 审批通过 / 驳回

前端展示改进（2026-05-28）：

- 表格新增"摘要"列，按 action 类型展示关键信息（消息内容、工具调用参数、API 路径等）
- 结果列翻译为中文（成功/失败/拒绝/执行中）
- 新增时间范围筛选（DatePicker）
- 点击详情按钮打开侧边抽屉，按事件类型结构化展示所有字段
- 补全 action 翻译（工具调用、审批操作等共 26 种）

审计数据文件：

```text
/Users/leo/.jotaduo.secret/jotaduo_audit.jsonl
```

核心代码：

```text
src/jotaduo_ext/jotaduo/audit.py
src/jotaduo/agents/tool_guard_mixin.py
console/src/jotaduo/pages/AuditLogs/index.tsx
```

### 菜单结构

当前菜单结构（2026-05-28 更新）：

- 工作区（agent-scoped，跟随当前选中智能体）
  - 工作区（文件浏览）
  - 频道
  - 定时任务
  - 技能
  - 技能池（Skill Pool）
  - 技能市场（Skill Market）
  - 工具
  - MCP
  - ACP
  - 插件管理
  - 智能体配置
- 安全管理
  - 安全设置
  - 审批中心
  - 日志审计
- 权限管理
  - 用户权限
  - 智能体授权
- 智能报表
  - 智能体统计
  - Token 消耗
- 控制
  - 会话管理
  - 心跳
- 设置
  - 账号设置
  - 智能体
  - 模型
  - 环境变量
  - 备份
  - 语音转写
  - Debug

注意：
- 聊天入口已从侧边栏菜单隐藏（用户通过智能体选择器上方的对话入口进入聊天）。
- 频道、技能池、技能市场、插件管理已从设置区移入工作区，因为这些功能与当前智能体强相关。
- 菜单名称和位置是产品化调整重点，后续改动应避免重复建设原项目已有功能。

## 当前智能体数据

智能体配置文件：

```text
/Users/leo/.jotaduo/config.json
```

当前确认存在 6 个智能体：

```text
default
Test-bot
AI-coding-bot
AI-ops
AI-minitor
JotaDuo_QA_Agent_0.2
```

智能体工作区：

```text
/Users/leo/.jotaduo/workspaces/default
/Users/leo/.jotaduo/workspaces/Test-bot
/Users/leo/.jotaduo/workspaces/AI-coding-bot
/Users/leo/.jotaduo/workspaces/AI-ops
/Users/leo/.jotaduo/workspaces/AI-minitor
/Users/leo/.jotaduo/workspaces/JotaDuo_QA_Agent_0.2
```

## 已知运维注意事项

### 启动必须使用 start-jotaduo-zh.sh

服务必须通过 `./start-jotaduo-zh.sh` 启动，不能直接运行 `jotaduo app`。

原因：启动脚本会设置 `JOTADUO_AUTH_ENABLED=true` 等环境变量。如果直接运行 `jotaduo app`，认证不会启用，所有页面和 API 都可以匿名访问（返回 `local-admin` 身份并拥有全部权限）。

排查方式：访问 `/api/auth/status`，确认 `"enabled": true`。

此问题在 2026-05-28 曾触发一次排查，确认不是代码 bug，是启动方式不正确。

## 最近一次严重事故与修复

### 现象

用户反馈：

- 用户管理页面只看到一个用户。
- 智能体页面看起来像数据丢失。
- 这是严重生产事故。

### 排查结论

实际数据没有物理丢失：

- `auth.json` 中仍有 11 个用户。
- `config.json` 中仍有 6 个智能体。
- 服务日志显示 `6/6 agents started successfully`。

真正原因：

- 权限治理升级后启用了更严格的智能体过滤。
- 治理文件中原本只有 `Test-bot` 一条智能体授权策略，其他智能体策略缺失。
- 早期 UI 曾把“工具授权给哪些智能体”的值保存到旧字段 `allowed_roles`。
- 新模型改为按 `allowed_agents` 判断，旧数据未迁移时导致工具 / MCP / Skill 授权被误隐藏。

### 修复方式

已执行数据修复：

- 补齐 6 个智能体授权策略。
- 补齐智能体排序中的缺失项。
- 把旧字段中实际属于智能体 ID 的值迁移到 `allowed_agents`。

已提交代码修复：

```text
6a901fc0 fix: preserve legacy agent resource grants
```

修复内容：

- 在 `governance.py` 中增加旧数据兼容逻辑。
- 如果 `allowed_agents` 为空，但旧字段 `allowed_roles` 中包含非内置角色 ID，则按旧智能体授权兼容识别。
- 增加回归测试，防止未来再次出现“数据存在但被权限过滤隐藏”的问题。

验证：

```text
63 passed, 1 warning
```

## 最近关键提交

```text
8f2fd623 docs: add startup auth caveat to handoff document
64ee9c7d docs: update handoff with v4 runtime config migration details
bd6a85c7 feat: migrate runtime config to PostgreSQL (v4)
96833215 docs: update project context with PostgreSQL migration and route guards
5882c5d4 docs: update project context and deployment guides for PostgreSQL
fbbcc9b6 chore: add PostgreSQL to Docker Compose and update build config
4de3e170 feat: integrate approval flow into MCP, skill and plugin operations
6a57ff7f feat: add PostgreSQL storage for users, roles and RBAC
94742567 feat: add PostgreSQL storage for governance data
92182b78 feat: add PostgreSQL storage for audit logs and approval requests
1f34e0c1 fix: enforce agent resource authorization on detail/action routes
77ebb2ab docs: add cj aiops project context handoff
6a901fc0 fix: preserve legacy agent resource grants
65c9e0a4 feat: audit agent tool execution lifecycle
cc79b6ff fix: enforce agent resource governance at runtime
b3c43d27 test: harden cj aiops governance controls
61b4ca27 docs: add company-grade engineering governance
34658c83 fix: make docker build compatible with local compose
426acb6c feat: add docker deployment support
```

## 现有文档索引

建议新会话按顺序阅读：

```text
docs/jotaduo-project-context.md
docs/technical-solution.md
docs/requirements-spec.md
docs/company-grade-engineering-governance.md
docs/docker-deployment-guide.md
docs/ops-platform-dev.md
```

## PostgreSQL 数据库化改造

### 双模式存储架构

所有二开数据层已改造为双模式：

- 配置 `JOTADUO_DB_URL` 环境变量时走 PostgreSQL。
- 未配置时继续走原有 JSON / JSONL 文件，适合本地开发。

技术选型：SQLAlchemy 2.x + Alembic + psycopg2。

### 已迁移到 PostgreSQL 的数据

| 数据 | 表名 | 仓库文件 |
| --- | --- | --- |
| 审计日志 | `audit_events` | `repositories/audit_postgres.py` |
| 审批请求 | `approval_requests` | `repositories/approval_postgres.py` |
| 智能体策略 | `jotaduo_agent_policies` | `repositories/governance_postgres.py` |
| 资源策略 | `jotaduo_resource_policies` | `repositories/governance_postgres.py` |
| 审批策略 | `jotaduo_approval_policies` | `repositories/governance_postgres.py` |
| 用户 | `jotaduo_users` | `repositories/auth_postgres.py` |
| 角色 | `jotaduo_roles` | `repositories/auth_postgres.py` |
| 用户角色关系 | `jotaduo_user_roles` | `repositories/auth_postgres.py` |
| 角色权限 | `jotaduo_role_permissions` | `repositories/auth_postgres.py` |
| 全局配置 (config.json) | `jotaduo_global_config` | `repositories/config_postgres.py` |
| 智能体配置 (agent.json) | `jotaduo_agent_configs` | `repositories/config_postgres.py` |
| 智能体-用户授权 | `jotaduo_agent_user_grants` | `repositories/agent_grants_postgres.py` |
| 能力审批配置 | `jotaduo_capability_approval_config` | `repositories/capability_approval_postgres.py` |
| 智能体模板 | `jotaduo_agent_templates` | `repositories/agent_templates_postgres.py` |

仍保留在文件侧：JWT 签名密钥、token 撤销列表（`auth.json` 中）。

运行时配置（v4）采用 JSONB 整体存储 + `SELECT ... FOR UPDATE` 行锁，解决并发写入丢更新问题。save 同时写入 PG 和文件，确保 CLI 工具和非 PG 环境正常工作。读取使用 `updated_at` 替代文件 mtime 做缓存失效判断，上层 70+ 调用点零改动。

### 迁移操作

```bash
# Alembic 建表
alembic upgrade head

# 文件数据导入 PostgreSQL（含运行时配置）
python scripts/jotaduo_migrate_files_to_postgres.py \
  --secret-dir /path/to/.jotaduo.secret \
  --working-dir /path/to/.jotaduo
```

### 运行时权限入口加固

已补全的后端资源守卫：

- `tools.py`：工具开关、配置读取 / 更新前校验智能体资源授权。
- `mcp.py`：MCP 详情、开关、更新、删除前校验。
- `skills.py`：Workspace Skill 启停、删除、文件、保存、配置、批量操作前校验。
- `plugins.py`：插件操作前校验。
- `proactive_responder.py`：主动响应注册工具前校验。
- `reme_light_memory_manager.py`：记忆总结 Toolkit 注册前校验。
- 回归测试：`tests/unit/jotaduo/test_resource_route_guards.py`。

## 端到端验证记录

### 多租户权限 E2E 验证 (2026-05-28)

14 项 API 验证全部通过，覆盖完整 CRUD 链路：

| 验证项 | 结果 |
| --- | --- |
| 能力审批配置列表 | 正常（5 类配置已初始化） |
| 审批配置部分更新 | 正常（tool add_approval 更新成功） |
| 智能体模板列表 | 正常（4 个内置模板） |
| 模板创建 | 正常 |
| 模板更新 | 正常 |
| 模板删除 | 正常 |
| 批量授权智能体给用户 | 正常（granted_count=2） |
| 查询智能体已授权用户 | 正常 |
| 查询用户已授权智能体 | 正常 |
| 批量撤销授权 | 正常（revoked_count=1） |
| 前端 TypeScript 编译 | 通过（0 errors） |
| 前端生产构建 | 通过（13s） |
| 后端单元测试 | 96 passed, 1 warning |
| 初始化脚本 | 幂等执行成功 |

### 首次 E2E 验证 (2026-05-28 早)

| 验证项 | 结果 |
| --- | --- |
| 前端页面加载 | 正常（HTML 返回 200） |
| 认证拦截 | 正常（无 token 请求均返回 401） |
| 登录接口 | 正常（zhangming/123456 获取 token） |
| 用户列表 | 正常（11 个用户） |
| 角色列表 | 正常（4 个角色：admin, ops_admin, operator, viewer） |
| 工具列表 | 正常 |
| 审批请求 | 正常 |
| 审计日志 | 正常 |

## 后续优先事项

建议后续继续做：

1. **聊天页智能体选择体验修复**：避免旧会话显示 `JotaDuo` 被误判为智能体丢失。
2. **100 用户 / 100 智能体试运行压测**：重点观察活跃智能体数、容器内存、CPU、数据库连接数和长任务卸载行为。
3. **审批流回归测试补全**：覆盖 MCP 新增、Skill 新增、插件安装、审批通过 / 驳回、自审批禁止、审批后授权联动。
4. **JWT secret 和 token 撤销列表迁移到 PG**：auth 链路最后一块未迁移的数据。
5. **审计日志导出功能**：支持按条件导出 CSV / Excel。
6. 完善审批流后续收口：补齐”新增工具”独立入口，增强审批通知、筛选和批量处理体验。
7. 继续减少对上游核心逻辑的侵入，把二开能力收敛到 `jotaduo_ext/jotaduo`。

已在历次接管中完成：

- 审批中心前端页面已新增到”安全管理”，可查看审批申请、审批规则，并支持通过 / 驳回申请；旧收件箱式审批入口已从侧边栏隐藏；前端已构建并复制到 `src/jotaduo/console/` 给后端托管。
- MCP 新增已接入审批流：开启认证且审批策略启用时，新增 MCP 会生成待审批申请，不直接写入智能体配置；审批通过后再写入配置并触发智能体重载。
- Skill 新增已接入审批流：智能体 Skill 手工创建、ZIP 上传、Hub 安装，公共 Skill 手工创建、ZIP 上传、Hub 导入、技能池广播下载，共 7 条路径全部生成待审批申请；审批通过后再写入对应智能体或公共技能池。池级内置导入（`pool/import-builtin`、`pool/upload`、`pool/{name}/update-builtin`）经确认不需要审批。
- 插件安装已接入审批流：路径 / URL 安装、ZIP 上传安装都会生成待审批申请；上传包先进入 `.jotaduo.secret` 下的审批暂存区，审批通过后再安装加载插件。
- 审批通过后已联动治理策略：面向单个智能体新增的 MCP / Skill 会自动授权给来源智能体；公共 Skill 和插件会自动进入治理台但默认不开放给所有智能体；治理台已支持展示和编辑插件资源。
- 审批接口已新增 `approval.manage` 权限，并默认授予 `admin`、`ops_admin`；审批策略配置已进入治理数据，第一阶段默认 `mcp.create`、`skill.create`、`tool.create` 由 `admin`/`ops_admin` 审批，`plugin.install` 仅由 `admin` 审批，且默认禁止自审批。
- 治理数据补齐逻辑已沉淀为启动迁移流程，会自动补齐智能体授权策略、兼容旧资源授权字段，并补齐智能体排序缺失项。
- 恢复前自动快照已调整为包含敏感数据目录，部署文档已明确 `JOTADUO_WORKING_DIR` 和 `JOTADUO_SECRET_DIR`，备份恢复要求覆盖 `.jotaduo` 和 `.jotaduo.secret`。
- 运行时权限入口已全面加固：工具、MCP、Skill、插件的详情 / 开关 / 更新 / 删除接口均补全智能体资源授权校验；非聊天路径的 Toolkit 注册也已纳入治理。
- 审计日志、审批请求、治理数据（智能体策略 / 资源策略 / 审批策略）、用户 / 角色 / RBAC 已全部支持 PostgreSQL 存储，采用双模式架构，Alembic 管理表结构迁移，统一迁移脚本支持文件到数据库的全量导入。
- v4 运行时配置入 PG：全局 config.json 和每智能体 agent.json 已迁入 PostgreSQL（JSONB + 行锁），在持久化边界（`load_config` / `save_config` / `load_agent_config` / `save_agent_config`）拦截，70+ 调用点自动切换，上游核心文件各加约 6 行。迁移脚本已扩展 `--working-dir` 参数，PG 容器验证全局配置 + 6 个智能体配置导入成功。
- 审计日志增强（2026-05-28）：后端 — 消息预览扩至 1000 字符，工具调用参数/结果扩至 2000 字符，`api.mutate` 新增查询参数记录，API 新增 `start_time`/`end_time` 时间范围筛选。前端 — 新增"摘要"列按 action 类型展示关键信息（消息内容、工具参数、API 路径等），结果列翻译中文，新增 DatePicker 时间范围筛选，点击详情打开侧边抽屉按事件类型结构化展示完整字段，action 翻译补全至 26 种含工具调用和审批操作。
- 智能体级文件隔离第一轮加固：文件预览接口和内置文件读写工具已限制在当前智能体 workspace 内，新增回归测试覆盖跨 workspace 访问拒绝。
- 多智能体运行时容量治理（2026-05-28）：`MultiAgentManager` 已支持默认最多 20 个活跃智能体（`JOTADUO_MAX_ACTIVE_AGENTS` 可调）、默认 1 小时空闲回收（`JOTADUO_AGENT_IDLE_TTL_SECONDS` 可调）、LRU 空闲智能体淘汰、跳过活跃任务卸载、启动预热按容量截断，其余智能体按首次访问懒加载。新增 `/api/agents/runtime` 状态接口、`/api/agents/runtime/cleanup-idle` 手动空闲清理、`/api/agents/{agentId}/runtime/unload` 手动卸载接口，并新增生命周期回归测试。
- Docker Compose 容量配置补齐（2026-05-28）：本地和服务器 Compose 均已配置应用 / PostgreSQL 默认 CPU、内存上限变量，并把 `JOTADUO_MAX_ACTIVE_AGENTS=20`、`JOTADUO_AGENT_IDLE_TTL_SECONDS=3600` 写入应用容器环境；部署文档已补充 100 用户 / 100 智能体试运行建议。
- **多租户权限体系重构（2026-05-28）**：将旧的「角色→智能体策略（visible/usable/manageable/allowed_roles）」替换为简洁的三层模型：平台访问（用户+角色→菜单）、智能体授权（admin 创建→grant 给用户）、能力审批（5 类×新增/删除/自动审批独立开关）。新增 `authorization.py`（核心授权判断）、`agent_grants.py`（授权 CRUD + 批量操作）、`capability_approval.py`（5 类审批配置）、`agent_templates.py`（4 内置模板 + 自定义），均支持文件 + PG 双模式。`agents.py` 路由层已切换到新 authorization 模块。前端「智能体授权」页改为三 Tab（Transfer 穿梭框选人 + 审批 Switch 矩阵 + 模板管理），「审批中心」审批规则切换到新 API。新增 Alembic 迁移 `0003_jotaduo_multi_tenant`（3 张表）。新增初始化脚本 `scripts/init_multi_tenant.py`。
- **旧 governance agent_policies 清理 + 前端资源过滤修复（2026-05-29）**：删除旧的 `role_ids_can_access_agent`、`filter_agent_ids_for_roles`、`ensure_agent_access`、`ensure_agent_resource_access`、`_capability_for_agent_path`、`_capability_for_header_agent_path` 等已被 authorization 模块替代的死代码。删除 `/governance/agent-policies` 三个路由端点和 `AgentAccessPolicy` 模型。前端删除对应接口定义。修复 `agents.py` 中 `list_agent_runtime` 调用未导入的 `filter_agent_ids_for_roles` 的运行时错误，改用 `filter_agent_ids_for_user`。前端 `useSkills`/`useTools`/`useMCP` 移除冗余 `filterResourcesByAgent` 客户端二次过滤（后端已统一处理）。资源过滤规则统一为"无策略或空 allowed_agents = 默认放行"。
- **能力审批配置策略枚举化 + PG 正式启用（2026-05-29）**：审批配置从混乱的 3 布尔字段（`add_approval`/`remove_approval`/`auto_approve_remove`）简化为 2 个策略枚举：`add_policy`（none/approval）、`remove_policy`（none/log/approval）。后端 Pydantic 模型、API handler、核心模块、PG schema、PG repository 全部改为新字段。`_migrate_legacy()` 保留旧布尔格式向后兼容。前端审批中心和智能体授权页从 3 个 Switch 改为 2 个 Select 下拉。新增 Alembic 迁移 `0004_cap_approval_enum`（自动检测表是否存在，处理 stamp-over 场景）。迁移脚本补齐 agent_grants / capability_approval / agent_templates 三类多租户数据的文件→PG 导入。**本地开发已正式启用 PG**：`start-jotaduo-zh.sh` 添加 `JOTADUO_DB_URL` 默认连接 `jotaduo-pg-test` 容器（127.0.0.1:5432），全部数据存储走 PostgreSQL。
- **角色体系精简为 2 角色（2026-05-29）**：admin（平台管理员，全部权限）+ operator（平台操作员，工作区权限）。清理 ops_admin / viewer。操作员定时任务权限、侧边栏菜单可见性已修复。删除操作自动审批记录已补齐（6 个 delete 端点）。
- **审计日志 CSV 导出（2026-05-29）**：后端新增 `/audit/events/export` 端点，支持按条件导出 UTF-8 BOM CSV（中文表头），最大 50000 行。前端审计日志页新增"导出 CSV"按钮。
- **系统健壮性加固（2026-05-29）**：9 项修复——①启动时 PG 健康检查（`check_database_health`）；②所有列表查询加 LIMIT 封顶（默认 1000，上限 5000）；③智能体级联删除（`cascade_delete_agent` 单事务清理 grants/policies/configs）；④`add_policy`/`remove_policy` 枚举值服务端校验；⑤审计写入 PG 失败自动 fallback 本地文件保底，日志升级 error；⑥连接池 pool_size 5→10，max_overflow 10→20；⑦PG 连接超时 `connect_timeout=5`；⑧所有 Pydantic Model 字符串字段加 `max_length`（标识符 256，描述 2000）；⑨能力审批配置改为原子 SQL 局部更新（`partial_update`），消除 read-modify-write 竞争。
- **100 用户容量调优（2026-05-29）**：PG 容器 `max_connections` 100→200、`shared_buffers` 128MB→256MB。启动脚本新增 `JOTADUO_MAX_ACTIVE_AGENTS=50`（20→50）、`JOTADUO_AGENT_IDLE_TTL_SECONDS=1800`（3600→1800，加速空闲回收释放内存给更多活跃 agent）。多 worker 模式不可用（上游 `MultiAgentManager` 内存状态不可跨进程共享），但 FastAPI async 单进程架构足以支撑 100 并发用户。
- **Schema 初始化性能优化（2026-05-29）**：`initialize_schema()` 从每次 API 请求都执行（42 个 repository 入口 × 20+ 条 CREATE TABLE/INDEX SQL）改为进程级只执行一次（`_schema_initialized` 标志），后续请求直接跳过。`reset_engine_cache()` 会同步重置标志，保证测试和配置重载场景正确。页面加载速度明显提升。
- **Hub 安装技能审批漏洞修复（2026-05-29）**：全量审计所有技能新增路径后发现 `POST /skills/hub/install/start` 缺少审批检查，用户可绕过审批直接从外部 Hub 安装任意技能到工作区。已补齐 `capability_create_requires_approval` 检查和 `submit_capability_approval` 提交，审批通过后由新增的 `workspace.hub_install` 执行器调用 `install_skill_from_hub` 完成安装并自动创建治理策略。池级入口（`pool/import-builtin`、`pool/upload`、`pool/{name}/update-builtin`）经用户确认不需要审批，保持原样。
- **用户取消智能体授权后登录报错修复（2026-05-29）**：授权撤销后 localStorage 仍存旧 agent_id，请求携带 `X-Agent-Id` 触发 403 "Agent access denied"。前端 `request.ts` 新增 `resetToValidAgent()` 拦截器，403 时自动重置到 `default` 智能体并异步刷新可用列表。
### Codex 接替 Claude 后工作记录（2026-05-29 晚）

接管后先通读交接文档并复核 Claude 下班前的最新改动状态，重点确认能力审批枚举、删除审批记录、审计 CSV 导出、PG 健康检查/连接池/LIMIT/fallback、两角色模型、启动脚本 PG 默认连接、迁移脚本和对应测试。随后围绕智能体隔离、权限审批、授权管理和本地服务状态继续推进。

已完成事项：

- **技能池广播权限与审批收口**：`GET /api/skills/workspaces` 已按当前用户智能体授权过滤，广播弹窗只显示可访问智能体；`POST /api/skills/pool/download` 后端强制校验显式目标和 `all_workspaces` 解析结果，预检查也不能探测无权智能体。实际广播下载现在作为 `skill.create` 审批申请提交（operation=`workspace.download_from_pool`），审批通过后再把公共技能池 Skill 写入目标工作区，并为该 Skill 补齐目标智能体治理授权。前端广播流程已支持 `pending_approval` 返回并提示“审批通过后生效”。补充单测覆盖广播提交审批、预检查越权拒绝、审批通过后执行下载。
- **智能体授权撤销保存修复**：定位到智能体授权页撤销用户时报 `422 Unprocessable Entity` 的根因是前端通用请求封装 `request()` 原先只为 POST/PUT/PATCH 自动设置 `Content-Type: application/json`，导致 `DELETE /api/jotaduo/agent-grants/{agent_id}` 的 JSON body 无法被 FastAPI 解析。现改为“请求带 body 即自动补 JSON Content-Type”，同时保持无 body 的 DELETE 不加 Content-Type。新增 `request.test.ts` 覆盖 DELETE 有 body/无 body 两个分支；前端生产构建已重新生成并同步到 `src/jotaduo/console/`。
- **本地服务启动脚本核对与恢复**：确认项目启动入口为 `./start-jotaduo-zh.sh`，脚本默认启用认证、连接 `postgresql+psycopg2://jotaduo:jotaduo_dev_password@127.0.0.1:5432/jotaduo`，并设置 `JOTADUO_MAX_ACTIVE_AGENTS=50`、`JOTADUO_AGENT_IDLE_TTL_SECONDS=1800`。修复前端构建同步后，原启动会话已退出且 8088 无监听；按用户要求直接执行启动脚本恢复服务。普通沙箱执行会被本机 PG 连接限制拦截，需使用已授权的启动脚本执行方式。本次恢复 PostgreSQL 健康检查通过，7/7 个智能体启动成功，新进程 PID `14756`，服务地址 `http://127.0.0.1:8088`，状态 `JotaDuo Ready`。
- **交付习惯约定**：用户已明确要求后续项目改动先出方案，确认后再继续；每次完成项目改动后必须把改动内容写入本交接文档，方便 Codex 与 Claude 交叉接管。

本次验证：

- `.venv/bin/python -m pytest -q tests/unit/jotaduo/test_approval_requests.py`：7 passed, 1 warning。
- `.venv/bin/python -m pytest -q tests/unit/jotaduo tests/unit/app/test_multi_agent_manager_lifecycle.py`：110 passed, 1 warning。
- `.venv/bin/python -m py_compile src/jotaduo/app/routers/skills.py src/jotaduo/app/routers/jotaduo.py tests/unit/jotaduo/test_approval_requests.py`：通过。
- `npm test -- request.test.ts`：14 passed。
- `npm run build`：通过，仅保留既有 Vite chunk/dynamic import 警告。
- `git diff --check`：通过。

当前注意事项：

- 当前工作区仍有未提交改动，覆盖技能池广播审批、授权撤销修复、前端构建同步和本文档更新；提交前需要再次检查 `git status`。
- 后端服务当前由 `./start-jotaduo-zh.sh` 启动，监听 `http://127.0.0.1:8088`。如服务中断，优先执行启动脚本，不要直接裸跑 `jotaduo app`，否则可能缺少认证和 PG 环境变量。
- 前端生产构建需要同步到 `src/jotaduo/console/` 后，后端托管页面才会使用最新 bundle。

## 当前测试状态

```text
110 passed, 1 warning
request.test.ts: 14 passed
```

测试命令：

```bash
cd /app
.venv/bin/python -m pytest -q tests/unit/app/test_multi_agent_manager_lifecycle.py tests/unit/jotaduo
cd console && npm test -- request.test.ts
cd console && npm run build
```

## 新会话接管提示词

新开 Codex 或 Claude Code 工作区后，可以直接发送：

```text
请先阅读 docs/jotaduo-project-context.md，然后继续接管Jotaduo AIops 平台项目。重点保持二开功能独立，避免重复建设原项目已有功能。
```

如果需要处理权限、智能体、工具、MCP、Skill、审计或部署问题，先查看本文档中的数据文件位置和最近事故记录。
