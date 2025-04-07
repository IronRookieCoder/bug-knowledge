# Bug知识库系统部署指南

## 环境要求

- Miniconda 或 Anaconda（推荐使用Miniconda以减少安装体积）
- Git
- Git Bash (Windows环境需要)

## Windows开发环境配置

1. 安装Miniconda
   - 从[官网](https://docs.conda.io/projects/miniconda/en/latest/)下载并安装Miniconda
   - 建议安装到默认路径

2. 克隆代码库
   ```bash
   git clone <repository_url>
   cd bug-knowledge
   ```

3. 复制环境变量模板
   ```bash
   cp .env.example .env
   ```
   根据实际情况修改.env文件中的配置

4. 初始化环境（在Git Bash中运行）
   ```bash
   chmod +x *.sh  # 确保脚本有执行权限
   ./rebuild.sh
   ```

5. 启动服务
   ```bash
   ./start.sh --mode web
   ```

## Linux生产环境部署

1. 安装Miniconda
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   chmod +x Miniconda3-latest-Linux-x86_64.sh
   ./Miniconda3-latest-Linux-x86_64.sh
   source ~/.bashrc
   ```

2. 克隆代码库
   ```bash
   git clone <repository_url>
   cd bug-knowledge
   ```

3. 复制环境变量模板
   ```bash
   cp .env.example .env
   ```
   修改.env文件：
   - 将 HOST 改为 0.0.0.0
   - 将 PYTHON_ENV 改为 production
   - 根据需要修改其他配置

4. 赋予脚本执行权限
   ```bash
   chmod +x *.sh
   ```

5. 初始化环境
   ```bash
   ./rebuild.sh
   ```

6. 启动服务
   - 前台运行（调试用）：
     ```bash
     ./start.sh --mode web --host 0.0.0.0 --port 8010
     ```
   - 后台运行（生产环境）：
     ```bash
     nohup ./start.sh --mode web --host 0.0.0.0 --port 8010 > nohup.out 2>&1 &
     ```

7. 查看服务状态
   ```bash
   ps aux | grep python
   tail -f nohup.out
   ```

## Docker部署

### 环境要求
- Docker Engine 20.10+
- Docker Compose V2

### 快速启动
1. 克隆代码库
   ```bash
   git clone <repository_url>
   cd bug-knowledge
   ```

2. 复制并配置环境变量
   ```bash
   cp .env.example .env
   ```
   按需修改 .env 文件中的配置

3. 构建并启动服务
   ```bash
   # 构建镜像
   docker compose build

   # 启动所有服务
   docker compose up -d

   # 仅启动特定服务
   docker compose up -d web   # 仅启动web服务
   ```

4. 查看服务状态
   ```bash
   # 查看所有容器状态
   docker compose ps

   # 查看服务日志
   docker compose logs -f web     # 查看web服务日志
   docker compose logs -f crawler # 查看爬虫服务日志
   ```

### 服务说明
- web: Web服务，提供用户界面和API接口
- crawler: 爬虫服务，定时抓取bug数据
- storage: 存储服务，处理数据存储和向量化

### 数据持久化
数据通过卷挂载持久化：
- ./data: 存储数据库文件和向量存储
- ./logs: 存储应用日志

### 更新部署
1. 拉取最新代码
   ```bash
   git pull
   ```

2. 重新构建并启动服务
   ```bash
   docker compose down        # 停止现有服务
   docker compose build      # 重新构建镜像
   docker compose up -d      # 启动服务
   ```

### 常见问题
1. 端口冲突
   - 修改 docker-compose.yml 中的端口映射
   - 默认映射端口为 8010，可改为其他未被占用的端口

2. 数据目录权限
   ```bash
   # 确保数据目录有正确权限
   sudo chown -R 1000:1000 data/
   sudo chown -R 1000:1000 logs/
   ```

## 注意事项

1. 路径处理
   - Windows使用反斜杠(\)作为路径分隔符
   - Linux使用正斜杠(/)作为路径分隔符
   - 代码中统一使用正斜杠(/)，Python会自动处理平台差异

2. 权限问题
   - Linux下注意文件和目录的权限设置
   - 确保data目录和logs目录可写

3. 网络配置
   - 开发环境使用127.0.0.1访问
   - 生产环境使用0.0.0.0允许外部访问
   - 确保防火墙允许相应端口访问

4. 环境管理
   - 使用conda管理环境，确保跨平台兼容性
   - 不要手动修改environment.yml，使用conda命令管理依赖

## 常见问题与解决

1. conda环境激活失败
   - Windows: 检查conda安装路径是否正确
   - Linux: 确保已执行source ~/.bashrc

2. 端口被占用
   - 使用netstat命令检查端口占用
   - 修改配置使用其他可用端口

3. 数据目录权限问题
   ```bash
   # Linux下设置目录权限
   chmod -R 755 data/
   chmod -R 755 logs/
   ```

## 更新部署

1. 拉取最新代码
   ```bash
   git pull
   ```

2. 重建环境（如果依赖有更新）
   ```bash
   ./rebuild.sh
   ```

3. 重启服务
   - Linux:
     ```bash
     ps aux | grep python  # 找到旧进程
     kill <pid>            # 关闭旧进程
     nohup ./start.sh --mode web --host 0.0.0.0 --port 8010 > nohup.out 2>&1 &  # 启动新进程
     ```