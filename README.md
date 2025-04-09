# BUG 知识库系统

基于 RAG（检索增强生成）技术的 BUG 知识库系统，支持存储和检索 BUG 相关信息，包括问题详情、代码上下文、错误日志和环境信息。

## 功能特点

- 支持多维度信息存储：问题描述、代码、日志、环境信息
- 基于向量相似度的智能检索
- 混合权重的多向量检索策略
- Web 界面支持
- 轻量级本地存储
- 支持计划任务自动执行
- 自动索引备份机制
- 支持 GitLab 和其他平台数据采集
- 支持 mock 数据测试

## 目录结构

```
bug-knowledge/
├── data/
│   ├── bugs.db         # SQLite数据库
│   ├── temp/           # 临时文件目录
│   └── annoy/          # 向量数据库存储目录
│       ├── code.ann    # 代码相关向量
│       ├── summary.ann # 摘要向量
│       ├── test_info.ann # 测试信息向量
│       ├── log_info.ann  # 日志向量
│       ├── environment.ann # 环境信息向量
│       ├── backup/     # 索引备份目录
│       └── temp/       # 临时向量文件
├── docs/               # 项目文档
│   ├── config_guide.md      # 配置指南
│   ├── deployment_guide.md  # 部署指南
│   └── *.puml              # 系统架构图
├── lm-models/          # 预训练模型
│   └── all-MiniLM-L6-v2/   # Sentence Transformer模型
├── logs/               # 日志目录
│   ├── bug_knowledge.log    # 生产环境日志
│   └── bug_knowledge_dev.log # 开发环境日志
├── mock/              # 测试数据和脚本
├── pip_cache/         # pip包缓存
├── src/               # 源代码
│   ├── crawler/       # 数据采集模块
│   ├── features/      # 特征提取模块
│   ├── models/        # 数据模型定义
│   ├── retrieval/     # 检索模块
│   ├── search/        # 搜索服务
│   ├── storage/       # 存储模块
│   ├── ui/            # Web界面
│   ├── utils/         # 工具函数
│   └── vectorization/ # 向量化模块
├── setup             # 环境配置脚本
├── docker-compose.yml  # Docker编排配置
└── Dockerfile         # Docker构建文件
```

## 系统要求

- Python 3.8 或更高版本
- 支持 Linux/MacOS/Windows

## 快速开始

1. 克隆仓库并进入项目目录

2. 运行环境配置脚本：
   ```bash
   # Linux/MacOS
   chmod +x setup
   ./setup

   # Windows (使用Git Bash)
   ./setup
   ```

此脚本会自动：
- 创建并激活 Conda 环境
- 安装项目依赖
- 创建必要的目录
- 下载预训练模型（如果需要）

3. 运行系统：
   ```bash
   # 完整模式
   python -m src --mode all

   # 开发环境 Web 服务
   python -m src --mode web

   # 生产环境 Web 服务
   python -m src --mode web --host 0.0.0.0 --port 8010
   ```

## 运行模式

系统支持以下运行模式：

1. 完整模式（采集、存储、Web服务）：
   ```bash
   python -m src --mode all
   ```

2. 仅数据采集：
   ```bash
   python -m src --mode crawler
   ```

3. 仅构建索引：
   ```bash
   python -m src --mode storage
   ```

4. 仅启动 Web 服务：
   ```bash
   python -m src --mode web
   ```

### 启动参数

- `--mode`: 运行模式 (crawler|storage|web|all)
- `--host`: Web 服务器主机地址（默认：127.0.0.1）
- `--port`: Web 服务器端口（默认：8010）
- `--schedule`: 启用计划运行模式
- `--hour`: 计划任务执行时间（小时，0-23）
- `--minute`: 计划任务执行时间（分钟，0-59）
- `--interval`: 任务执行间隔（小时）

### 计划任务示例

1. 每天凌晨 2 点执行：
   ```bash
   python -m src --mode all --schedule --hour 2 --minute 0
   ```

2. 每 12 小时执行一次：
   ```bash
   python -m src --mode all --schedule --interval 12
   ```

## Docker 部署

系统提供了 Docker 支持，可以使用 Docker Compose 快速部署：

1. 构建镜像：
   ```bash
   docker compose build
   ```

2. 启动服务：
   ```bash
   docker compose up -d
   ```

3. 查看日志：
   ```bash
   docker compose logs -f
   ```

4. 停止服务：
   ```bash
   docker compose down
   ```

### 数据持久化

Docker 部署时以下数据通过卷挂载持久化：
- `./data`: 数据库文件和向量存储
- `./logs`: 应用日志
- `./lm-models`: 预训练模型

## 技术架构

系统采用模块化设计，主要包含以下组件：

1. 数据采集模块（Crawler）

   - GitLab 代码变更采集
   - 支持多数据源集成
   - 智能 Bug ID 识别

2. 向量化模块（Vectorization）

   - 基于 Sentence Transformers 的文本向量化
   - 多维度特征提取
   - 支持增量更新

3. 存储模块（Storage）

   - 基于 Annoy 的向量存储
   - SQLite 关系型存储
   - 自动备份机制

4. 检索模块（Retrieval）

   - 多向量混合检索
   - 可配置的权重策略
   - LRU 缓存优化

5. Web 界面（UI）
   - 响应式设计
   - 实时搜索
   - 结果可视化

## 向量检索权重

系统默认的检索权重配置：

- 摘要信息：20%
- 代码相关：25%
- 测试信息：15%
- 日志信息：30%
- 环境信息：10%

可通过配置文件调整权重分配。

## 数据备份

系统采用多层次的自动备份机制：

1. 向量索引备份：
   - 位置：`data/annoy/backup/`
   - 备份格式：`YYYYMMDD_HHMMSS/`
   - 包含文件：所有.ann索引文件的完整副本
   - 触发时机：
     - 索引更新时
     - 每日定时备份
     - 大规模数据导入后

2. 数据库备份：
   - SQLite数据库文件自动备份
   - 增量事务日志
   - 定期完整备份

3. 备份管理：
   - 自动清理过期备份
   - 保留最近30天的备份
   - 每月保留一个完整备份
   - 重要更新时刻的备份永久保留

## 注意事项

1. 首次运行需要下载预训练模型，请确保 `lm-models` 目录下已包含所需模型
2. 确保有足够的磁盘空间用于数据存储和索引备份
3. 在生产环境中建议：
   - 启用计划任务模式
   - 定期检查备份
   - 配置适当的检索权重
4. 开发测试时可使用 mock 数据

## 许可证

MIT License
