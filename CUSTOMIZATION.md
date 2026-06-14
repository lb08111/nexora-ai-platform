# Jotaduo AIops 平台二开说明

本文档记录当前项目基于 JotaDuo 的二次开发内容、后续同步原项目更新的方式，以及托管到 GitHub 前的注意事项。

## 项目定位

- 上游项目：`agentscope-ai/QwenPaw`
- 二开项目：Jotaduo AIops 平台
- 当前本地目录：`/app`
- 本地访问地址：`http://127.0.0.1:8088`

当前建议把本项目作为长期维护的产品分支，而不是一次性改动。后续原项目升级时，通过 Git 的 upstream/origin 机制合并更新。

## 已完成的二开内容

- 中文化：前端默认语言、后端默认语言、登录页标题和主要界面文案。
- 品牌化：登录页、浏览器标题、favicon、页面 logo 替换为Jotaduo AIops 平台品牌。
- 登录认证：启用登录页，未登录访问受保护页面时跳转登录。
- 用户体系：补充用户管理、角色管理、权限管理接口和页面。
- 权限体系：后端 API 增加权限校验能力，前端增加用户权限管理入口。
- 菜单结构：设置菜单支持展开/折叠，账号管理归入设置二级菜单。
- 退出登录：移动到页面右上角。
- 模型配置：本地已验证 MiniMax 国内端点可用，密钥保存在本机配置目录，不应提交到仓库。
- 外网访问验证：已验证可通过 Cloudflare Tunnel 临时地址访问本地服务。

## 重点改动文件

- `start-jotaduo-zh.sh`
- `console/index.html`
- `console/src/i18n.ts`
- `console/src/App.tsx`
- `console/src/layouts/Header.tsx`
- `console/src/layouts/Sidebar.tsx`
- `console/src/layouts/index.module.less`
- `console/src/locales/zh.json`
- `console/src/locales/en.json`
- `console/src/pages/Login/index.tsx`
- `console/src/jotaduo/api/users.ts`
- `console/src/jotaduo/pages/UserManagement/`
- `console/public/logo.png`
- `console/public/logo-icon.svg`
- `src/jotaduo_ext/jotaduo/`
- `src/jotaduo/app/auth.py`
- `src/jotaduo/app/routers/auth.py`
- `src/jotaduo/app/routers/settings.py`
- `docs/ops-platform-dev.md`

## 二开隔离约定

后续Jotaduo AIops 业务代码优先放在独立扩展目录，原项目只保留必要挂载点：

- 后端扩展目录：`src/jotaduo_ext/jotaduo/`
- 前端扩展目录：`console/src/jotaduo/`

新增用户权限、运维工具、审批、审计、MCP/Skill 接入时，默认先放到这些目录。只有注册路由、注册菜单、接入中间件时，才少量修改 JotaDuo 原生文件。

## 后续同步上游更新

推荐保留两个远端：

- `upstream`：原始 JotaDuo 仓库
- `origin`：Jotaduo AIops 自己的 GitHub 仓库

首次整理远端时：

```bash
git remote rename origin upstream
git remote add origin git@github.com:<your-org-or-user>/jotaduo-platform.git
git fetch upstream
```

以后同步上游时：

```bash
git fetch upstream
git checkout main
git checkout -b sync/upstream-YYYYMMDD
git merge upstream/main
```

合并后需要重点验证：

- 登录页是否能打开
- 登录 / 退出是否正常
- 用户、角色、权限页面是否正常
- 聊天页是否正常
- 设置菜单展开折叠是否正常
- 前端是否能成功构建
- 后端是否能正常启动

对于长期产品分支，优先使用 merge 保留历史，不建议频繁 rebase 主分支。

## GitHub 托管前检查

提交前不要包含以下内容：

- 模型 API Key
- `.env` / `.env.*`
- 本地用户配置和密钥目录
- Cloudflare Tunnel 凭证
- `node_modules`
- `.venv`
- `logs`
- 构建产物
- 本地下载的二进制工具，例如 `bin/cloudflared`

推荐先建私有仓库，确认没有敏感信息后再决定是否开放。

## 推荐提交方式

建议把当前二开作为第一批提交：

```bash
git add .gitignore CUSTOMIZATION.md docs/ops-platform-dev.md start-jotaduo-zh.sh
git add console/index.html console/public console/src
git add src/jotaduo/app/auth.py src/jotaduo/app/routers/auth.py src/jotaduo/app/routers/settings.py
git commit -m "Add jotaduo platform customization"
```

推送到自己的 GitHub：

```bash
git push -u origin main
```
