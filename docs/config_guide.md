# 配置指南

## 环境配置

本项目使用 Conda 管理 Python 环境，使用 pip 安装额外的依赖包。

### 环境设置

1. 确保已安装 Conda
2. 运行环境配置脚本：
   ```bash
   ./setup
   ```

### 环境文件说明

- `environment.yml`: Conda 环境配置文件，包含基础 Python 环境和核心依赖
- `requirements.txt`: pip 依赖包列表，包含项目特定的依赖

## 配置文件结构

本系统使用分层的环境配置文件来管理不同环境的配置：

1. `.env` - 基础配置文件，包含默认配置
2. `.env.[environment]` - 环境特定配置（development/production）
3. `.env.local` - 本地开发配置（不提交到版本控制）

## 配置项说明

### 必需配置项
- `DATABASE_PATH`: 数据库文件路径
- `APP_PORT`: 应用程序端口（1024-65535）

### 应用配置
- `DEBUG`: 是否开启调试模式
- `APP_NAME`: 应用名称
- `APP_PORT`: 应用端口号
- `WEB_HOST`: Web服务主机地址

### 数据存储配置
- `DATABASE_PATH`: SQLite数据库路径
- `VECTOR_STORE_DIR`: 向量存储目录
- `VECTOR_DIM`: 向量维度
- `INDEX_TYPE`: 索引类型
- `N_TREES`: 树的数量

### 备份配置
- `BACKUP_ROOT`: 备份根目录（默认: data/backup/）
- `BACKUP_KEEP_DAYS`: 常规备份保留天数（默认: 30）
- `BACKUP_MIN_MONTHLY`: 每月最少保留备份数（默认: 1）
- `BACKUP_MAX_MONTHLY`: 每月最多保留备份数（默认: 3）
- `BACKUP_COMPRESSION`: 是否压缩备份（默认: True）
- `VECTOR_BACKUP_DIR`: 向量索引备份目录（默认: data/annoy/backup/）
- `DB_BACKUP_DIR`: 数据库备份目录（默认: data/backup/db/）
- `CONFIG_BACKUP_DIR`: 配置备份目录（默认: data/backup/config/）

### 数据源配置
- `GITLAB_URLS`: GitLab服务器URL列表（|分隔）
- `GITLAB_TOKENS`: GitLab访问令牌列表（|分隔）
- `GITLAB_PROJECT_IDS`: GitLab项目ID列表（组内逗号分隔，组间|分隔）
- `TD_URLS`: TD系统URL列表（|分隔）
- `TD_COOKIES`: TD系统Cookie列表（|分隔）
- `PRODUCT_IDS`: 产品ID列表
- `TD_AREA`: TD系统区域列表

### 日志配置
- `LOG_LEVEL`: 日志级别（DEBUG/INFO/WARNING/ERROR）
- `LOG_FILE`: 日志文件路径
- `LOG_MAX_SIZE`: 日志文件最大大小（字节）
- `LOG_BACKUP_COUNT`: 日志文件备份数量
- `LOG_FORMAT`: 日志格式

### 调度配置
- `SCHEDULE_TYPE`: 调度类型（daily/monthly/interval）
  - daily: 每日执行，指定时间
  - monthly: 每月执行，指定日期和时间
  - interval: 间隔执行，指定小时数
- `SCHEDULE_DAY`: 月度调度时的执行日期（1-31），仅在 monthly 模式下使用
- `SCHEDULE_HOUR`: 执行时间（小时，0-23），在 daily 和 monthly 模式下使用
- `SCHEDULE_MINUTE`: 执行时间（分钟，0-59），在 daily 和 monthly 模式下使用
- `SCHEDULE_INTERVAL`: 间隔执行的小时数，仅在 interval 模式下使用

注意：这些配置项可以通过命令行参数覆盖，优先级：命令行参数 > 环境变量 > 默认值

## 环境特定配置

### 开发环境（.env.development）
- DEBUG=True
- 较小的日志文件大小和备份数量
- HOST=127.0.0.1

### 生产环境（.env.production）
- DEBUG=False
- 较大的日志文件大小和备份数量
- HOST=0.0.0.0
- 配置更大的备份保留期限
- 启用压缩备份
- 配置专门的备份目录

### 本地配置（.env.local）
用于覆盖环境配置，适用于：
- 本地测试配置
- 敏感信息（tokens、cookies）
- 临时配置
- 自定义备份策略

## 配置验证

系统启动时会验证：
1. 必需配置项完整性
2. 端口号有效性（1024-65535）
3. 目录权限和可访问性
4. 向量存储配置的完整性
5. 备份目录的可写性
6. 备份配置的合理性
