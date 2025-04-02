# 配置管理指南

## 配置文件结构

项目使用分层配置文件结构：

- `.env.example` - 配置模板，包含所有可配置项
- `.env` - 基础配置文件
- `.env.development` - 开发环境配置
- `.env.test` - 测试环境配置
- `.env.production` - 生产环境配置
- `.env.local` - 本地开发配置（不进入版本控制）

## 环境切换

通过设置 `PYTHON_ENV` 环境变量来切换环境：

```bash
# Windows
set PYTHON_ENV=development
# Linux/MacOS
export PYTHON_ENV=production
```

## 配置项说明

### 应用配置

- `DEBUG`: 是否开启调试模式 (true/false)
- `APP_NAME`: 应用名称
- `APP_PORT`: 应用端口号 (1024-65535)

### 数据库配置

- `DATABASE_PATH`: 数据库文件路径

### GitLab 配置

- `GITLAB_URLS`: GitLab 服务器地址，多个地址用逗号分隔
- `GITLAB_TOKENS`: GitLab 访问令牌
- `GITLAB_PROJECT_IDS`: 项目 ID 列表

### TD 系统配置

- `TD_URLS`: TD 系统地址
- `TD_COOKIES`: TD 系统 Cookie

### 日志配置

- `LOG_LEVEL`: 日志级别 (DEBUG/INFO/WARNING/ERROR)
- `LOG_FILE`: 日志文件路径

## 使用示例

```python
from src.config import config

# 获取配置
debug_mode = config.debug
app_port = config.get_int('APP_PORT')
gitlab_urls = config.get_list('GITLAB_URLS')

# 获取必需配置（不存在会抛出异常）
database_path = config.get_required('DATABASE_PATH')

# 获取布尔类型配置
is_debug = config.get_bool('DEBUG', default=False)
```

## 最佳实践

1. 不要在代码中硬编码配置值
2. 区分开发和生产环境配置
3. 使用类型安全的配置获取方法
4. 配置变更需要经过验证
5. 保持配置模板(.env.example)更新
