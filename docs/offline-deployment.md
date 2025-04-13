# Bug Knowledge 离线部署文档

## 1. 环境要求

### 1.1 目标服务器要求

- 操作系统：CentOS 7
- Docker：版本 >= 20.10.0
- Docker Compose：版本 >= 1.29.0
- Python：版本 3.8.x（推荐）

### 1.2 系统要求

1. 磁盘空间：

   - 系统分区：至少 5GB 可用空间
   - 数据分区：根据数据量大小，建议至少 10GB
   - Docker 数据目录(/var/lib/docker)：至少 10GB 可用空间

2. 内存要求：

   - 最小：4GB RAM
   - 推荐：8GB RAM

3. CPU 要求：

   - 最小：2 核心
   - 推荐：4 核心

4. 用户权限：
   - 需要 root 权限执行安装
   - 容器运行使用非特权用户

### 1.3 CentOS 7 环境准备

1. 安装 Docker：

   ```bash
   # 安装必要的依赖
   yum install -y yum-utils device-mapper-persistent-data lvm2

   # 添加Docker仓库
   yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

   # 安装Docker
   yum install -y docker-ce docker-ce-cli containerd.io

   # 启动Docker服务
   systemctl start docker
   systemctl enable docker
   ```

2. 安装 Docker Compose：

   ```bash
   # 下载Docker Compose
   curl -L "https://github.com/docker/compose/releases/download/1.29.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

   # 添加执行权限
   chmod +x /usr/local/bin/docker-compose
   ```

3. 配置防火墙：

   ```bash
   # 开放Docker端口
   firewall-cmd --permanent --add-port=8010/tcp
   firewall-cmd --reload
   ```

4. 配置 SELinux：

   ```bash
   # 临时关闭SELinux
   setenforce 0

   # 永久关闭SELinux（需要重启）
   sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
   ```

### 1.4 网络要求

- 部署环境：可以是完全离线环境
- 内部网络：确保容器可以与内部服务通信
- 端口：8010 需要开放给用户访问

## 2. 准备离线部署包

### 2.1 在开发环境准备

1. 确保开发环境已安装：

   ```bash
   # 安装pip
   python -m ensurepip --upgrade

   # 安装必要的工具
   pip install docker-compose
   ```

2. 执行准备脚本：

   ```bash
   # 给脚本添加执行权限
   chmod +x prepare-offline.sh

   # 执行准备脚本
   ./prepare-offline.sh
   ```

3. 脚本执行完成后，将在当前目录生成：
   - `bug-knowledge-offline.tar.gz`：离线部署包
   - `deployment/README.md`：部署说明文档

### 2.2 部署包内容说明

部署包包含以下内容：

- `Dockerfile`：Docker 构建文件
- `docker-compose.yml`：容器编排配置
- `docker-entrypoint.sh`：容器启动脚本
- `requirements.txt`：Python 依赖列表
- `packages/`：离线 Python 依赖包
- `python/`：Python 3.8 安装包
- `rpms/`：系统依赖包
- `src/`：项目源代码
- `data/`：数据备份（如果有）

## 3. 离线环境部署

### 3.1 前置条件

1. 确保目标服务器已安装 Docker：

   ```bash
   # 检查Docker版本
   docker --version

   # 检查Docker Compose版本
   docker-compose --version
   ```

2. 将部署包传输到目标服务器：
   ```bash
   # 使用scp或其他方式传输
   scp bug-knowledge-offline.tar.gz user@target-server:/path/to/deploy
   ```

### 3.2 执行部署

1. 登录目标服务器：

   ```bash
   ssh user@target-server
   ```

2. 执行部署脚本：

   ```bash
   # 进入部署目录
   cd /path/to/deploy

   # 给脚本添加执行权限
   chmod +x deploy-offline.sh

   # 执行部署脚本（需要root权限）
   sudo ./deploy-offline.sh
   ```

### 3.3 验证部署

1. 检查容器状态：

   ```bash
   docker-compose ps
   ```

2. 查看容器日志：

   ```bash
   docker-compose logs -f
   ```

3. 访问应用：
   - Web 界面：http://服务器 IP:8010
   - API 接口：http://服务器 IP:8010/api

## 4. 配置说明

### 4.1 环境变量配置

可以通过修改 `docker-compose.yml` 文件配置以下参数：

| 参数名   | 说明                 | 默认值  |
| -------- | -------------------- | ------- |
| MODE     | 运行模式             | web     |
| HOST     | 监听地址             | 0.0.0.0 |
| PORT     | 监听端口             | 8010    |
| SCHEDULE | 是否启用定时任务     | 空      |
| HOUR     | 定时任务小时         | 2       |
| MINUTE   | 定时任务分钟         | 0       |
| INTERVAL | 定时任务间隔（小时） | 24      |

### 4.2 数据持久化

- 应用数据存储在 Docker 卷中
- 数据位置：`/var/lib/docker/volumes/`
- 建议定期备份数据卷

## 5. 常见问题

### 5.1 部署失败

- 检查 Docker 和 Docker Compose 版本
- 检查 Python 版本是否为 3.8
- 查看部署日志：`docker-compose logs -f`
- 检查 SELinux 状态：`getenforce`
- 检查防火墙状态：`firewall-cmd --state`
- 检查磁盘空间：`df -h`
- 检查内存使用：`free -h`

### 5.2 应用无法访问

- 检查防火墙设置
- 确认端口 8010 是否开放
- 检查容器状态：`docker-compose ps`
- 检查 SELinux 是否阻止访问：
  ```bash
  # 查看SELinux日志
  ausearch -m AVC -ts recent
  ```

### 5.3 网络排查

- 检查内部网络连接：

  ```bash
  # 进入容器内部
  docker exec -it <container_id> bash

  # 测试与其他服务的连接
  curl -v <internal_service>
  ```

- 检查 DNS 解析：

  ```bash
  # 检查DNS配置
  cat /etc/resolv.conf

  # 测试DNS解析
  nslookup <domain>
  ```

- 检查网络设置：
  ```bash
  # 查看Docker网络
  docker network ls
  docker network inspect bridge
  ```

### 5.4 定时任务不执行

- 检查 SCHEDULE 参数设置
- 检查 HOUR 和 MINUTE 参数
- 查看容器日志：`docker-compose logs -f`
- 检查系统时间是否正确：

  ```bash
  # 查看系统时间
  date

  # 设置系统时间
  timedatectl set-time "YYYY-MM-DD HH:MM:SS"
  ```

## 6. 维护说明

### 6.1 更新应用

1. 在开发环境准备新的部署包
2. 将新部署包传输到目标服务器
3. 停止旧容器：
   ```bash
   # 进入部署包解压后的deployment目录
   cd /path/to/deploy/deployment
   docker-compose down
   ```
4. 执行新的部署脚本
   ```bash
   # 返回到部署包所在目录
   cd ..
   sudo ./deploy-offline.sh
   ```

### 6.2 备份数据

1. 确保 `prepare-offline.sh` 脚本已执行，并且生成的 `deployment/data/data.tar.gz` 文件是最新的备份（如果需要手动执行特定备份）。
2. 或者，手动执行备份命令（确保容器已停止或应用处于非写入状态以保证一致性）：

   ```bash
   # 停止容器（推荐）
   # cd /path/to/deploy/deployment && docker-compose down

   # 创建备份目录（如果需要）
   mkdir -p /path/to/backup

   # 执行备份
   docker run --rm -v bug-knowledge:/source -v /path/to/backup:/backup \
       alpine tar -czf /backup/data_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /source .

   # 重启容器（如果之前已停止）
   # cd /path/to/deploy/deployment && docker-compose up -d
   ```

   _请将 `/path/to/backup` 替换为您希望存储备份文件的实际路径。_
   _`bug-knowledge` 是 `docker-compose.yml` 中定义的卷名。_

### 6.3 恢复数据

1. 确保目标服务器上存在数据备份文件（例如 `/path/to/backup/data_backup_YYYYMMDD_HHMMSS.tar.gz`）。
2. 停止当前运行的容器：
   ```bash
   cd /path/to/deploy/deployment
   docker-compose down
   ```
3. （可选，但推荐）移除或重命名现有的 Docker 卷以进行干净恢复：
   ```bash
   docker volume rm bug-knowledge
   # 或者 docker volume rename bug-knowledge bug-knowledge_old
   ```
4. 执行恢复命令：

   ```bash
   # 确保存储备份文件的目录存在
   ls /path/to/backup/data_backup_YYYYMMDD_HHMMSS.tar.gz

   # 执行恢复
   docker run --rm -v bug-knowledge:/target -v /path/to/backup:/backup \
       alpine sh -c "cd /target && tar -xzf /backup/data_backup_YYYYMMDD_HHMMSS.tar.gz"
   ```

   _请将 `/path/to/backup/data_backup_YYYYMMDD_HHMMSS.tar.gz` 替换为实际的备份文件路径。_
   _如果之前没有移除卷，此操作会将备份文件解压并覆盖现有卷中的内容。_

5. 重启容器：
   ```bash
   docker-compose up -d
   ```

## 7. 联系支持

如遇到问题，请联系技术支持：

- 邮箱：support@example.com
- 电话：xxx-xxxx-xxxx
