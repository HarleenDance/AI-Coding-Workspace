# Jenkins 一键部署指南

适用项目：`HarleenDance/AI-Coding-Workspace.git`

目标：Jenkins 每次拉取 GitHub 最新代码后，自动构建前端、后端 Docker 镜像，并通过 Docker Compose 启动：

- 前端：http://localhost/
- 后端：http://localhost:8000/api
- 数据库：localhost:5433
- Jenkins：http://localhost:8080/

## 1. 前置要求

Jenkins 所在机器需要安装：

1. Git
2. Docker Desktop 或 Docker Engine
3. Docker Compose v2
4. Jenkins Pipeline 插件

在 Jenkins 节点上执行下面命令确认：

```powershell
git --version
docker --version
docker compose version
```

如果 Jenkins 是 Windows 服务运行，需要确认 Jenkins 服务账号有权限访问 Docker。

## 2. 推荐 Job 类型

推荐创建：

```text
Pipeline
```

或者：

```text
Multibranch Pipeline
```

最简单方式用普通 Pipeline。

## 3. 创建 Pipeline Job

如果你想用脚本一键创建 Jenkins Job，可以在项目根目录执行：

```powershell
.\deploy\create-jenkins-job.ps1 `
  -JenkinsUrl "http://localhost:8080" `
  -JobName "AI-Coding-Workspace" `
  -RepoUrl "https://github.com/HarleenDance/AI-Coding-Workspace.git" `
  -Branch "main"
```

如果 Jenkins 开启了登录认证，需要传用户名和 API Token：

```powershell
.\deploy\create-jenkins-job.ps1 `
  -JenkinsUrl "http://localhost:8080" `
  -Username "你的Jenkins用户名" `
  -ApiToken "你的Jenkins API Token" `
  -JobName "AI-Coding-Workspace" `
  -RepoUrl "https://github.com/HarleenDance/AI-Coding-Workspace.git" `
  -Branch "main"
```

脚本会创建或更新 Pipeline Job，并配置 `Poll SCM`：

```text
H/2 * * * *
```

也可以按下面步骤在页面手动创建。

1. 打开 Jenkins：

```text
http://localhost:8080/
```

2. 点击：

```text
New Item
```

3. 输入 Job 名称：

```text
AI-Coding-Workspace
```

4. 选择：

```text
Pipeline
```

5. 点击 OK。

## 4. 配置 GitHub 仓库

进入 Job 配置页，找到：

```text
Pipeline → Definition
```

选择：

```text
Pipeline script from SCM
```

SCM 选择：

```text
Git
```

Repository URL：

```text
https://github.com/HarleenDance/AI-Coding-Workspace.git
```

Branch：

```text
*/main
```

Script Path：

```text
Jenkinsfile
```

保存。

## 5. 配置 API Key

如果你只是部署页面和基础功能，可以暂时不填模型 key。

如果要真实调用模型，在 Jenkins Job 配置里添加环境变量，或使用 Jenkins Credentials 绑定：

```text
DB_PASSWORD=你的数据库密码
DEEPSEEK_API_KEY=你的 DeepSeek Key
DASHSCOPE_API_KEY=你的 DashScope Key
```

当前部署脚本会优先读取 Jenkins 环境变量，并写入项目根目录 `.env`。

## 6. 手动构建

Job 页面点击：

```text
Build Now
```

构建完成后访问：

```text
http://localhost/
```

后端健康检查：

```text
http://localhost:8000/api/health/db
```

## 7. 每次更新自动构建

有两种方式。

### 方式 A：Jenkins 轮询 GitHub

Job 配置里勾选：

```text
Poll SCM
```

Schedule 填：

```text
H/2 * * * *
```

表示大约每 2 分钟检查一次 GitHub 更新。

### 方式 B：GitHub Webhook

如果 Jenkins 能被 GitHub 访问，在 GitHub 仓库中配置 Webhook：

```text
Payload URL: http://你的 Jenkins 地址/github-webhook/
Content type: application/json
Events: Just the push event
```

本地 Jenkins 是 `localhost:8080` 时，GitHub 无法直接访问。可以用内网穿透工具，或者先使用 Poll SCM。

## 8. Jenkinsfile 做了什么

`Jenkinsfile` 分三步：

1. Checkout：拉取 GitHub 最新代码。
2. Docker Info：检查 Docker 和 Docker Compose。
3. Build & Deploy：调用部署脚本。

Windows 节点调用：

```powershell
deploy/jenkins-deploy.ps1
```

Linux 节点调用：

```bash
deploy/jenkins-deploy.sh
```

## 9. 部署脚本做了什么

部署脚本会执行：

```text
检查 docker
准备 .env
构建后端镜像 app-backend:latest
构建前端镜像 app-frontend:latest
docker compose up -d db
docker compose up -d backend frontend
检查后端健康状态
打印访问地址
```

## 10. 常见问题

### 10.1 Jenkins 端口是 8080，会不会和项目冲突？

不会。

项目默认端口：

```text
前端：80
后端：8000
数据库：5433
Jenkins：8080
```

### 10.2 访问 http://localhost/ 打不开

检查容器：

```powershell
docker compose ps
```

查看前端日志：

```powershell
docker compose logs --tail=100 frontend
```

### 10.3 后端健康检查失败

查看后端日志：

```powershell
docker compose logs --tail=120 backend
```

查看数据库日志：

```powershell
docker compose logs --tail=120 db
```

### 10.4 Docker build 很慢

第一次构建会下载 Python、Node、Nginx、Postgres 镜像，比较慢。

后续构建会复用缓存。

如果要完全重建，在 Jenkins 构建参数里勾选：

```text
NO_CACHE
```

### 10.5 GitHub 拉取失败

如果本机访问 GitHub 慢或失败，可以在 Jenkins 节点上配置 Git 代理：

```powershell
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

## 11. 本地直接执行部署

不用 Jenkins 时，也可以在项目根目录执行：

```powershell
.\deploy\jenkins-deploy.ps1
```

Linux：

```bash
bash deploy/jenkins-deploy.sh
```
