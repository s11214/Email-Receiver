# 使用官方的 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到容器的工作目录
COPY . /app

# 安装依赖包
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 Flask 应用运行的端口（5000）
EXPOSE 5000

# 设置环境变量，告诉 Flask 应用在容器中运行
ENV FLASK_RUN_HOST=0.0.0.0

# 运行 Flask 应用
CMD ["python", "app.py"]
