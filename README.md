# Docker Web Pusher

**Docker Web Pusher** 是一个基于 Web 的 Docker 镜像管理与推送工具。它提供了一个直观的图形界面，帮助用户轻松管理 Docker 项目、构建镜像、备份数据，并一键推送到远程仓库。

## 🚀 核心特性

- **可视化项目管理**：轻松创建和编辑 Docker 项目配置。
- **✨ 多架构构建 (Multi-arch)**：集成 Docker Buildx，支持一键同时构建 `amd64`, `arm64`, `riscv64` 等多种架构的镜像。
- **✨ 环境自愈系统**：内置环境自检与“一键修复”功能，自动配置 QEMU 模拟器和多架构 Builder，换机无忧。
- **✨ 多标签一次性推送**：支持使用 `|` 或逗号分隔多个 Tag（如 `v1|latest`），一次构建，全量推送。
- **✨ 自动清理功能**：支持构建成功后自动删除本地镜像标签，有效节省宿主机磁盘空间。
- **网络代理支持**：支持配置 HTTP/HTTPS 代理，并能自动注入到 Dockerfile 中，解决网络连接问题。
- **本地备份管理**：支持镜像的本地备份与恢复（支持 7z 高效压缩）。
- **实时日志监控**：通过 WebSocket 提供实时的构建（包含 Buildx 过程）与推送日志流。

## 🛠️ 技术栈

本项目采用现代化的前后端分离架构：

- **前端**：Vue 3, Element Plus, Pinia, Vite
- **后端**：Python 3.11, FastAPI, SQLAlchemy, Docker SDK, Buildx CLI
- **部署**：Docker, Docker Compose (多阶段构建)

## 📦 安装与使用

### 前置要求

- 操作系统：Linux (推荐), macOS, Windows (WSL2)
- 环境依赖：Docker Engine, Docker Compose

### 快速开始

创建一个 `docker-compose.yml` 文件：

```yaml
services:
  docker-pusher:
    image: pipi20xx/dockerhub-web-box
    container_name: dockerhub-web-box
    ports:
      - "7222:8000"
    volumes:
      - ./data:/app/data    # 数据存储
      - /var/run/docker.sock:/var/run/docker.sock # 映射 docker 核心
      - /your/projects:/projects # 挂载你需要构建的项目路径
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped
```

1. **启动服务**：`docker-compose up -d`
2. **访问应用**：打开浏览器访问 `http://localhost:7222`

## 💡 高级用法说明

### 1. 多架构构建环境初始化
首次在 Linux 服务器上使用多架构构建时，如果顶部显示“环境未就绪”，只需点击 **[一键修复环境]**。程序会自动：
- 安装 QEMU 静态模拟器。
- 创建名为 `web-pusher-builder` 的专用容器驱动 Builder。

### 2. 多标签输入规范
在项目的 Tag 输入框中，您可以灵活使用以下分隔符：
- **竖线 (推荐)**：`v1.0|latest`
- **逗号**：`v1.0,latest` 或 `v1.0，latest` (支持全角)

### 3. 自动清理
开启“构建后清理”开关后，系统会在镜像成功 Push 到远程仓库后，自动删除本地产生的临时镜像标签，防止 `/var/lib/docker` 目录爆满。

## 📂 目录结构

```text
/dockerhub-web-box/
├── backend/            # Python FastAPI 后端
├── frontend/           # Vue.js 前端
├── data/               # 持久化数据 (数据库, 备份, 日志)
├── Dockerfile          # 多阶段构建文件 (内置 Docker CLI)
└── docker-compose.yml  # Compose 配置文件
```

## 🛡️ 安全提醒

- **Docker Socket**：本工具需要挂载 `/var/run/docker.sock`。请确保仅在受信任的网络环境中使用，或为 Web 界面增加一层 Nginx 基础认证。

## 📄 许可证

本项目开源，遵循 MIT License。