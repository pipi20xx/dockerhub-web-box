# --- STAGE 1: Frontend Builder ---
# 使用Node.js镜像作为前端构建环境
FROM node:20-alpine AS frontend-builder

# 设置前端构建的工作目录
WORKDIR /frontend-build

# 复制package.json和lock文件，利用缓存
COPY frontend/package*.json ./
RUN npm install

# 复制所有前端源代码
COPY frontend/ ./

# 执行构建命令，生成静态文件
RUN npm run build


# --- STAGE 2: Final Backend Image ---
# 使用Python镜像作为最终的应用环境
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 设置后端应用的工作目录
WORKDIR /app

# 安装Python依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 安装 7z 工具以支持更高效的压缩
RUN apt-get update && apt-get install -y p7zip-full && rm -rf /var/lib/apt/lists/*

# 复制后端应用代码
# 注意：我们只复制backend目录，保持镜像干净
COPY backend/ ./

# ✨ 关键一步：从前端构建阶段复制编译好的静态文件
# 将它们复制到后端应用的一个名为 "static" 的子目录中
COPY --from=frontend-builder /frontend-build/dist /app/static

# 暴露端口
EXPOSE 8000

# 定义容器启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]