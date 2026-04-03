FROM python:3.11-slim

# 防止 python生成.pyc文件
ENV PYTHONDONTWRITEBYTECODE=1

# 让日志直接输出到stout
ENV PYTHONUNBUFFERED=1

# 容器内工作目录
WORKDIR /app

# 先复制依赖文件
COPY requirements.txt /app/

# 安装依赖
RUN pip install --no-cache-dir --progress-bar off -i http://folib.fullgoalos.com.cn/storages/fg-pypi/central --trusted-host folib.fullgoalos.com.cn -r requirements.txt

# 复制项目文件
COPY . /app/

# 暴露端口
EXPOSE 8023

# 启动服务器
CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8023"]