# 使用CentOS 7基础镜像以匹配目标环境
FROM centos:7

# 设置工作目录
WORKDIR /app

# 安装基本系统依赖
RUN yum install -y \
    gcc \
    make \
    zlib-devel \
    bzip2-devel \
    openssl-devel \
    ncurses-devel \
    sqlite-devel \
    readline-devel \
    tk-devel \
    gdbm-devel \
    db4-devel \
    libpcap-devel \
    xz-devel \
    libffi-devel \
    curl \
    && yum clean all

# 复制Python安装包
COPY python/Python-3.8.0.tgz /tmp/
COPY python/Python-3.8.0.tgz.asc /tmp/

# 安装Python 3.8
RUN cd /tmp && \
    tar -xzf Python-3.8.0.tgz && \
    cd Python-3.8.0 && \
    ./configure --enable-optimizations && \
    make -j $(nproc) && \
    make altinstall && \
    cd / && \
    rm -rf /tmp/Python-3.8.0*

# 设置Python环境变量
ENV PATH="/usr/local/bin:${PATH}"

# 复制项目文件
COPY . /app/

# 复制Python依赖包
COPY packages /app/packages/

# 安装Python依赖
RUN python3.8 -m pip install --no-index --find-links=/app/packages -r requirements.txt

# 创建数据目录
RUN mkdir -p /app/data && \
    chmod 777 /app/data

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 确保脚本可执行
RUN chmod +x docker-entrypoint.sh

# 设置容器启动命令
ENTRYPOINT ["./docker-entrypoint.sh"]