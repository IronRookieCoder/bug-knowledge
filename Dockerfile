# 使用较新的Python基础镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/

# 安装 Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

# 设置conda环境变量
ENV PATH="/opt/conda/bin:${PATH}"

# 创建并激活conda环境
RUN conda env create -f environment.yml && \
    echo "conda activate bug-knowledge" >> ~/.bashrc

# 设置默认shell为bash，这样可以使用conda环境
SHELL ["/bin/bash", "--login", "-c"]

# 设置容器启动命令
ENTRYPOINT ["./docker-entrypoint.sh"]