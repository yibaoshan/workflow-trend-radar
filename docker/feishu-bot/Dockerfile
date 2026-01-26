# Feishu Trend Bot - Dockerfile

FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据和日志目录
RUN mkdir -p /data /app/logs

# 暴露端口
EXPOSE 9001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# 启动应用
CMD ["python", "-m", "feishu_bot.main"]
