# 配置指南

本系统使用分层的环境配置文件来管理不同环境的配置。配置文件按以下优先级从低到高加载：

1. `.env` - 基础配置文件，包含所有环境共享的默认配置
2. `.env.[environment]` - 环境特定配置文件（development/production）
3. `.env.local` - 本地开发配置（不应提交到版本控制）

## 必需的配置项

以下配置项必须在相应的环境中设置：

- `DATABASE_PATH`: 数据库文件路径
- `APP_PORT`: 应用程序端口（1024-65535）

## 配置项说明

### 应用配置

- `DEBUG`: 是否开启调试模式
- `APP_NAME`: 应用名称
- `APP_PORT`: 应用端口号

### 数据库配置

- `DATABASE_PATH`: SQLite 数据库路径

### GitLab 配置

使用`|`分隔多个配置项：

- `GITLAB_URLS`: GitLab 服务器 URL 列表
- `GITLAB_TOKENS`: GitLab 访问令牌列表
- `GITLAB_PROJECT_IDS`: GitLab 项目 ID 列表（每组用逗号分隔，组间用|分隔）
- `GITLAB_SINCE_DATE`: 抓取数据的起始日期
- `GITLAB_UNTIL_DATE`: 抓取数据的结束日期

### TD 系统配置

同样使用`|`分隔多个配置：

- `TD_URLS`: TD 系统 URL 列表
- `TD_COOKIES`: TD 系统 Cookie 列表
- `PRODUCT_IDS`: 产品 ID 列表
- `TD_AREA`: TD 系统区域列表

### 向量存储配置

- `VECTOR_STORE_DIR`: 向量存储目录
- `VECTOR_DIM`: 向量维度
- `INDEX_TYPE`: 索引类型
- `N_TREES`: 树的数量

### Web 服务配置

- `TEMPLATES_DIR`: 模板目录
- `STATIC_DIR`: 静态文件目录
- `WEB_HOST`: Web 服务主机地址
- `WEB_PORT`: Web 服务端口

### 日志配置

- `LOG_LEVEL`: 日志级别（DEBUG/INFO/WARNING/ERROR）
- `LOG_FILE`: 日志文件路径
- `LOG_MAX_SIZE`: 日志文件最大大小（字节）
- `LOG_BACKUP_COUNT`: 日志文件备份数量
- `LOG_FORMAT`: 日志格式

## 环境特定配置

### 开发环境（.env.development）

开发环境默认启用调试模式，使用较小的日志文件大小和备份数量。

### 生产环境（.env.production）

生产环境禁用调试模式，使用更大的日志文件大小和更多的备份数量。建议将数据存储路径配置到特定的数据目录。

## 本地配置

创建 `.env.local` 文件来覆盖任何环境配置，此文件不应提交到版本控制系统。适用于：

- 本地测试的特定配置
- 敏感信息（如 tokens 和 cookies）
- 临时配置

## 配置验证

系统会在启动时验证必需的配置项，确保：

1. 所有必需的配置项都已设置
2. 端口号在有效范围内（1024-65535）
3. 所有必需的目录都存在或可以创建
4. 向量存储配置的完整性
