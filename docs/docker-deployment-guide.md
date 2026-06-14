# Jotaduo AIops 平台 Docker 一键部署说明

本文档说明本项目如何改造成 Docker 一键部署，以及另一台 Linux 服务器如何在“不拉源码”的情况下部署运行。

## 1. 部署目标

本项目基于 JotaDuo 二次开发，前端、后端、权限体系、智能体权限、审计日志等能力都已经包含在代码仓库中。Docker 化后的目标是：

- 开发机负责构建镜像。
- 镜像包含前端构建产物和 Python 后端应用。
- 服务器只需要 Docker，不需要 Node、Python、源码和构建环境。
- 运行数据、密钥、备份通过 Docker volume 持久化。
- 后续升级只需要拉取新镜像并重启容器。

## 2. 当前 Docker 化改造内容

本次改造围绕上游已有容器能力进行增强，避免重复维护两套 Docker 逻辑：

- `deploy/Dockerfile`：正式镜像构建入口，负责构建前端并打包后端。
- `docker-compose.yml`：本地构建和本机运行使用。
- `deploy/docker-compose.server.yml`：服务器免源码部署使用。
- `.dockerignore`：减少构建上下文，避免把本地缓存、日志、密钥和临时文件打进镜像。
- `scripts/docker_build.sh`：统一镜像构建脚本，默认镜像名改为 `jotaduo-platform:latest`。

## 3. 镜像里包含什么

镜像构建过程分为两段：

第一段构建前端：

- 使用 Node 环境进入 `console` 目录。
- 安装前端依赖。
- 执行前端生产构建。
- 生成的控制台页面被复制到后端静态资源目录。

第二段构建运行环境：

- 安装 Python、Chromium、Supervisor 等运行依赖。
- 安装项目 Python 包。
- 设置默认运行目录：
  - `/app/working`
  - `/app/working.secret`
  - `/app/working.backups`
- 启动时自动初始化配置。
- 通过 `jotaduo app --host 0.0.0.0 --port 8088` 提供 Web 服务。

## 4. 本地构建镜像

在开发机项目根目录执行：

```bash
cd /app
bash scripts/docker_build.sh jotaduo-platform:latest
```

也可以直接用 Compose 构建并启动：

```bash
cd /app
docker compose up -d --build
```

启动后访问：

```text
http://127.0.0.1:8088
```

## 5. 本地停止和查看状态

查看容器：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f jotaduo
```

停止服务：

```bash
docker compose down
```

只停止服务不会删除数据卷。数据仍保存在 Docker volume 中。

## 6. 发布镜像到 GitHub Container Registry

推荐使用 GitHub Container Registry，镜像地址建议为：

```text
ghcr.io/lb08111/jotaduo-platform:latest
```

登录 GitHub 镜像仓库：

```bash
echo <你的_GitHub_Token> | docker login ghcr.io -u lb08111 --password-stdin
```

构建并打标签：

```bash
cd /app
bash scripts/docker_build.sh ghcr.io/lb08111/jotaduo-platform:latest
```

推送：

```bash
docker push ghcr.io/lb08111/jotaduo-platform:latest
```

如果要保留版本号，建议同时推送：

```bash
docker tag ghcr.io/lb08111/jotaduo-platform:latest ghcr.io/lb08111/jotaduo-platform:v0.1.0
docker push ghcr.io/lb08111/jotaduo-platform:v0.1.0
```

## 7. 另一台 Linux 服务器免源码部署

服务器只需要安装 Docker 和 Docker Compose 插件。

### 7.1 安装 Docker

Ubuntu / Debian 可执行：

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

验证：

```bash
docker --version
docker compose version
```

### 7.2 准备部署目录

```bash
sudo mkdir -p /opt/jotaduo
sudo chown -R $USER:$USER /opt/jotaduo
cd /opt/jotaduo
```

### 7.3 创建 Compose 文件

在服务器创建 `/opt/jotaduo/docker-compose.yml`：

```yaml
volumes:
  jotaduo-data:
    name: jotaduo-data
  jotaduo-secrets:
    name: jotaduo-secrets
  jotaduo-backups:
    name: jotaduo-backups

services:
  jotaduo:
    image: ghcr.io/lb08111/jotaduo-platform:latest
    container_name: jotaduo-platform
    restart: unless-stopped
    ports:
      - "127.0.0.1:8088:8088"
    environment:
      JOTADUO_AUTH_ENABLED: "true"
      JOTADUO_PORT: "8088"
      JOTADUO_WORKING_DIR: "/app/working"
      JOTADUO_SECRET_DIR: "/app/working.secret"
      JOTADUO_BACKUP_DIR: "/app/working.backups"
      JOTADUO_OPENAPI_DOCS: "false"
    volumes:
      - jotaduo-data:/app/working
      - jotaduo-secrets:/app/working.secret
      - jotaduo-backups:/app/working.backups
```

这里默认只监听服务器本机 `127.0.0.1`，适合前面再接 Nginx 或 Cloudflare Tunnel。

### 7.4 启动服务

```bash
cd /opt/jotaduo
docker compose pull
docker compose up -d
```

查看状态：

```bash
docker compose ps
docker compose logs -f jotaduo
```

服务器本机访问：

```bash
curl http://127.0.0.1:8088
```

## 8. 绑定公网访问

### 8.1 推荐方式：Nginx + HTTPS

安装 Nginx：

```bash
sudo apt install -y nginx
```

创建站点配置：

```nginx
server {
    listen 80;
    server_name aiops.example.com;

    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用站点后重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

再用 Certbot 申请 HTTPS：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d aiops.example.com
```

### 8.2 临时方式：Cloudflare Tunnel

如果暂时没有公网 IP 或域名，可以用 Cloudflare Tunnel：

```bash
cloudflared tunnel --url http://127.0.0.1:8088
```

这会生成一个临时公网地址。临时地址适合测试，不建议长期生产使用。

## 9. 升级流程

开发机完成代码更新后：

```bash
cd /app
bash scripts/docker_build.sh ghcr.io/lb08111/jotaduo-platform:latest
docker push ghcr.io/lb08111/jotaduo-platform:latest
```

服务器升级：

```bash
cd /opt/jotaduo
docker compose pull
docker compose up -d
docker image prune -f
```

数据卷不会因为升级镜像而丢失。

## 10. 回滚流程

如果发布了版本号，例如 `v0.1.0`、`v0.1.1`，服务器只需要修改镜像：

```yaml
image: ghcr.io/lb08111/jotaduo-platform:v0.1.0
```

然后执行：

```bash
cd /opt/jotaduo
docker compose pull
docker compose up -d
```

## 11. 备份数据

查看数据卷：

```bash
docker volume ls | grep jotaduo
```

备份数据卷：

```bash
mkdir -p /opt/jotaduo-backup
docker run --rm \
  -v jotaduo-data:/data \
  -v /opt/jotaduo-backup:/backup \
  busybox tar czf /backup/jotaduo-data.tar.gz -C /data .

docker run --rm \
  -v jotaduo-secrets:/data \
  -v /opt/jotaduo-backup:/backup \
  busybox tar czf /backup/jotaduo-secrets.tar.gz -C /data .

docker run --rm \
  -v jotaduo-backups:/data \
  -v /opt/jotaduo-backup:/backup \
  busybox tar czf /backup/jotaduo-backups.tar.gz -C /data .
```

其中 `jotaduo-secrets` 里会包含密钥和敏感配置，备份文件必须妥善保管。

## 12. 从本地迁移到服务器

如果要把开发机已有平台数据迁移到服务器，需要迁移以下目录内容：

- 工作目录：`.jotaduo`
- 密钥目录：`.jotaduo.secret`
- 备份目录：`.jotaduo.backups`

建议做法：

1. 先在服务器启动一次容器，让 Docker volume 自动创建。
2. 停止容器。
3. 把本地数据打包上传服务器。
4. 解压到对应 Docker volume。
5. 重新启动容器。

停止容器：

```bash
cd /opt/jotaduo
docker compose down
```

导入数据示例：

```bash
docker run --rm \
  -v jotaduo-data:/data \
  -v /opt/jotaduo-migration:/backup \
  busybox sh -c "rm -rf /data/* && tar xzf /backup/jotaduo-data.tar.gz -C /data"
```

密钥目录和备份目录同理处理。

## 13. 生产环境建议

- 不要直接把容器端口暴露到 `0.0.0.0`，优先通过 Nginx 或 Cloudflare Tunnel 暴露。
- 保持 `JOTADUO_AUTH_ENABLED=true`。
- 定期备份 `jotaduo-secrets`、`jotaduo-data` 和 PostgreSQL 数据库。
- 镜像发布建议使用版本号，不要只依赖 `latest`。
- 公网访问必须配置 HTTPS。
- 后续如果接入生产运维工具，建议先配置审批流和审计日志保留策略。

### 运行时容量建议

`docker-compose.yml` 和 `deploy/docker-compose.server.yml` 已内置服务健康检查：
PostgreSQL 使用 `pg_isready`，应用使用 `/api/version`。Compose 同时提供默认
资源上限，避免 100 个智能体配置场景下一次性占满主机资源：

```bash
export JOTADUO_APP_CPUS=2.0
export JOTADUO_APP_MEMORY_LIMIT=4g
export JOTADUO_POSTGRES_CPUS=1.0
export JOTADUO_POSTGRES_MEMORY_LIMIT=1g
export JOTADUO_MAX_ACTIVE_AGENTS=20
export JOTADUO_AGENT_IDLE_TTL_SECONDS=3600
```

对 100 用户 / 100 智能体的内部试运行，建议先保持最多 20 个活跃智能体、
1 小时空闲卸载；如果并发聊天明显超过 20 个智能体，再逐步提高
`JOTADUO_MAX_ACTIVE_AGENTS`，同时观察容器内存、CPU 和数据库连接数。

### PostgreSQL 存储

当前 Docker Compose 已包含 PostgreSQL 服务。应用通过以下变量启用
Jotaduo 数据库存储：

```text
JOTADUO_DB_URL=postgresql+psycopg2://jotaduo:<password>@postgres:5432/jotaduo
```

当前 PostgreSQL 化覆盖：

- 审计日志 `audit_events`
- 审批请求 `approval_requests`
- 智能体治理、资源授权和审批策略
- 用户、角色和角色权限

JWT 签名密钥和 token 撤销列表仍保留在密钥目录的 `auth.json`，
因此生产环境仍需要备份 `jotaduo-secrets`。

服务器部署前需要设置数据库密码：

```bash
export JOTADUO_POSTGRES_PASSWORD='<强密码>'
docker compose -f deploy/docker-compose.server.yml up -d
```

首次启用 PostgreSQL 后，可以把现有本地文件导入数据库。迁移脚本会导入
`jotaduo_audit.jsonl`、`jotaduo_approval_requests.json`、
`jotaduo_governance.json` 和 `auth.json` 中的用户/角色数据：

```bash
cd /opt/jotaduo
docker compose exec jotaduo alembic upgrade head
docker compose exec jotaduo \
  python /app/scripts/jotaduo_migrate_files_to_postgres.py \
  --secret-dir /app/working.secret
```

如果使用外部 PostgreSQL，可以不使用 Compose 内置 `postgres` 服务，
但必须为应用容器提供 `JOTADUO_DB_URL`，并确保网络可达。

## 14. 常见问题

### 容器启动后访问不到

检查容器状态：

```bash
docker compose ps
docker compose logs -f jotaduo
```

如果 Compose 里是 `127.0.0.1:8088:8088`，外部电脑不能直接访问服务器 IP 的 8088，需要通过 Nginx、Cloudflare Tunnel 或改成 `0.0.0.0:8088:8088`。

### 登录失败

先查看日志：

```bash
docker compose logs -f jotaduo
```

确认是否正确启用了认证，以及数据卷是否沿用了旧环境的用户配置。必要时先备份数据卷，再重置认证配置。

### 更新后页面还是旧版本

执行：

```bash
docker compose pull
docker compose up -d --force-recreate
```

然后浏览器强制刷新。

### 镜像拉取失败

检查：

- GitHub 镜像是否已经推送。
- GHCR 包是否公开，或服务器是否已经 `docker login ghcr.io`。
- 服务器网络是否能访问 `ghcr.io`。
