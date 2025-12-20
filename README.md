# Docker Web Pusher

**Docker Web Pusher** 是一个基于 Web 的 Docker 镜像管理与推送工具。它提供了一个直观的图形界面，帮助用户轻松管理 Docker 项目、构建镜像、备份数据以及将其推送到 Docker Hub 或本地私有仓库。

## 🚀 功能特性

- **可视化项目管理**：轻松创建和编辑 Docker 项目配置。
- **一键构建与推送**：集成 Docker 构建流程，支持一键将镜像推送到远程仓库。
- **网络代理支持**：支持配置 HTTP/HTTPS 代理，解决网络连接问题。
- **本地备份管理**：支持镜像的本地备份与恢复（支持 7z 高效压缩）。
- **实时日志监控**：通过 WebSocket 提供实时的构建与推送日志流，并在界面直观展示。
- **历史记录**：查看过往的任务执行历史和日志。

## 🛠️ 技术栈

本项目采用现代化的前后端分离架构：

- **前端**：Vue 3, Element Plus, Pinia, Vue Router, Vite
- **后端**：Python 3.11, FastAPI, SQLAlchemy, Uvicorn
- **部署**：Docker, Docker Compose (多阶段构建)

## 📦 安装与使用

### 前置要求

- 操作系统：Linux (推荐), macOS, Windows (WSL2)
- 环境依赖：Docker Engine, Docker Compose

### 快速开始 (使用预构建镜像)

创建一个 `docker-compose.yml` 文件并粘贴以下内容：

```yaml
services:
  docker-pusher:
    image: pipi20xx/dockerhub-web-box
    container_name: dockerhub-web-box
    ports:
      - "7222:8000"
    volumes:
      - ./data:/app/data    # 数据存储位
      - /var/run/docker.sock:/var/run/docker.sock # 映射 docker 核心
      - /vol1/1000/NVME:/vol1/1000/NVME # 挂载你需要构建的项目文件路径
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped
```

1. **启动服务**：
   ```bash
   docker-compose up -d
   ```

2. **访问应用**：
   打开浏览器访问 `http://localhost:7222` (或服务器 IP:7222)。

### 📸 简易设置说明

![设置说明](1.png)

### 从源码构建

如果你想自己构建镜像或进行二次开发：

1. **克隆仓库**：
   ```bash
   git clone <repository-url>
   cd dockerhub-web-box
   ```

2. **构建并启动**：
   ```bash
   docker-compose up -d --build
   ```

3. **访问应用**：
   访问 `http://localhost:7222`。

## 📂 目录结构

```text
/dockerhub-web-box/
├── backend/            # Python FastAPI 后端代码
├── frontend/           # Vue.js 前端代码
├── data/               # 持久化数据 (数据库, 备份, 日志)
├── docker-compose.yml  # 用于构建和开发的 Compose 文件
├── docker-compose-run.yml # 用于直接运行镜像的 Compose 文件
└── Dockerfile          # 多阶段构建文件
```

## 🛡️ 注意事项

- **Docker Socket**：容器需要挂载 `/var/run/docker.sock` 以便调用宿主机的 Docker 引擎执行构建和推送任务。请确保运行环境的安全性。
- **数据持久化**：所有的配置数据（数据库）和备份文件都存储在 `./data` 目录下，升级容器时请勿删除该目录。

## 📄 许可证

本项目开源，遵循 MIT License。
