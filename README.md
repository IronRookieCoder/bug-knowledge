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
│   └── annoy/          # 向量数据库存储目录
│       └── backup/     # 索引备份目录
├── docs/               # 项目文档
├── lm-models/          # 预训练模型
├── src/
│   ├── __main__.py    # 程序入口
│   ├── config.py      # 配置管理
│   ├── crawler/       # 数据采集模块
│   ├── features/      # 特征提取模块
│   ├── models/        # 数据模型定义
│   ├── retrieval/     # 检索模块
│   ├── search/        # 搜索服务
│   ├── storage/       # 存储模块
│   ├── ui/            # Web界面
│   ├── utils/         # 工具函数
│   └── vectorization/ # 向量化模块
├── mock/              # 测试数据
├── start.sh          # 启动脚本
└── rebuild.sh        # 环境重建脚本
```

## 系统要求

- Python 3.8 或更高版本
- 支持 Linux/MacOS/Windows

## 快速开始

1. 克隆仓库并进入项目目录

2. 运行环境重建脚本：

```bash
./rebuild.sh
```

此脚本会自动：

- 检查 Python 版本
- 创建虚拟环境
- 安装所需依赖
- 升级 pip

3. 使用启动脚本运行系统：

```bash
./start.sh --mode all
```

## 运行模式

系统支持以下运行模式：

1. 完整模式：

```bash
./start.sh --mode all
```

2. 仅数据采集：

```bash
./start.sh --mode crawler
```

3. 仅构建索引：

```bash
./start.sh --mode storage
```

4. 仅启动 Web 服务：

```bash
./start.sh --mode web
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
./start.sh --mode all --schedule --hour 2 --minute 0
```

2. 每 12 小时执行一次：

```bash
./start.sh --mode all --schedule --interval 12
```

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

系统自动对向量索引进行备份：

- 位置：`data/annoy/backup/`
- 时间戳命名：`YYYYMMDD_HHMMSS`
- 触发时机：索引更新时

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
