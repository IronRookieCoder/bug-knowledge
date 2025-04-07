# Bug知识库系统部署指南

## 环境要求

- Miniconda 或 Anaconda（推荐使用Miniconda以减少安装体积）
- Git
- Git Bash (Windows环境需要)

## 环境配置

### 快速配置（所有平台通用）

统一的环境配置脚本会自动检测操作系统并执行相应的配置：

```bash
# 确保脚本有执行权限（Linux环境需要）
chmod +x setup        # 仅Linux环境需要
# 运行配置脚本
./setup
```

### Windows 环境注意事项

1. 安装Miniconda
   - 从[官网](https://docs.conda.io/projects/miniconda/en/latest/)下载并安装Miniconda
   - 建议安装到默认路径
   - 确保在安装时添加到系统环境变量

2. 使用 Git Bash
   - 确保使用 Git Bash 而不是 CMD 或 PowerShell
   - Git Bash 提供了类Unix环境，确保脚本兼容性

### Linux 环境注意事项

1. Miniconda安装
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   chmod +x Miniconda3-latest-Linux-x86_64.sh
   ./Miniconda3-latest-Linux-x86_64.sh
   source ~/.bashrc
   ```

2. 权限设置
   ```bash
   chmod +x setup
   ```

## 基础部署步骤

1. 克隆代码库并进入目录
   ```bash
   git clone <repository_url>
   cd bug-knowledge
   ```

2. 配置环境（使用统一配置脚本）
   ```bash
   ./setup
   ```

3. 复制环境变量模板
   ```bash
   cp .env.example .env
   ```
   按需修改 .env 文件中的配置

4. 启动服务
   - 开发环境：
     ```bash
     python -m src --mode web
     ```
   - 生产环境：
     ```bash
     python -m src --mode web --host 0.0.0.0 --port 8010
     ```
   - 后台运行（生产环境）：
     ```bash
     nohup python -m src --mode web --host 0.0.0.0 --port 8010 > nohup.out 2>&1 &
     ```

## Docker部署

### 环境要求
- Docker Engine 20.10+
- Docker Compose V2

### 快速启动
1. 克隆并配置
   ```bash
   git clone <repository_url>
   cd bug-knowledge
   cp .env.example .env
   ```

2. 构建并启动服务
   ```bash
   docker compose build    # 构建镜像
   docker compose up -d    # 启动所有服务
   ```

### 服务说明
- web: Web服务，提供用户界面和API接口
- crawler: 爬虫服务，定时抓取bug数据
- storage: 存储服务，处理数据存储和向量化

### 数据持久化
数据通过卷挂载持久化：
- ./data: 存储数据库文件和向量存储
- ./logs: 存储应用日志

## 注意事项

1. 路径处理
   - Windows使用反斜杠(\)作为路径分隔符
   - Linux使用正斜杠(/)作为路径分隔符
   - 代码中统一使用正斜杠(/)，Python会自动处理平台差异

2. 权限问题
   - Linux下注意文件和目录的权限设置
   - 确保data目录和logs目录可写
     ```bash
     chmod -R 755 data/ logs/
     ```

3. 网络配置
   - 开发环境使用127.0.0.1访问
   - 生产环境使用0.0.0.0允许外部访问
   - 确保防火墙允许相应端口访问

## 更新部署

1. 更新代码和环境
   ```bash
   git pull
   conda env update -f environment.yml
   ```

2. 重启服务
   ```bash
   # 找到并关闭旧进程
   ps aux | grep python
   kill <pid>
   
   # 启动新进程（生产环境）
   nohup python -m src --mode web --host 0.0.0.0 --port 8010 > nohup.out 2>&1 &
   ```