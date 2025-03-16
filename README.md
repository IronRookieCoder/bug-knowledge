# BUG 知识库系统

基于 RAG（检索增强生成）技术的 BUG 知识库系统，支持存储和检索 BUG 相关信息，包括问题详情、代码上下文、错误日志和环境信息。

## 功能特点

- 支持多维度信息存储：问题描述、代码、日志、环境信息
- 基于向量相似度的智能检索
- 混合权重的多向量检索策略
- 命令行交互界面
- 轻量级本地存储

## 目录结构

```
bug-knowledge/
├── data/
│   └── chroma/          # 向量数据库存储目录
├── src/
│   ├── __init__.py
│   ├── __main__.py      # 程序入口
│   ├── models/
│   │   └── bug_models.py    # 数据模型定义
│   ├── vectorization/
│   │   └── vectorizers.py   # 向量化器实现
│   ├── storage/
│   │   └── vector_store.py  # 向量存储实现
│   ├── retrieval/
│   │   └── searcher.py      # 检索模块实现
│   └── ui/
│       └── cli.py           # 命令行界面实现
├── requirements.txt     # 项目依赖
└── README.md           # 项目文档
```

### 目录说明

- `data/chroma/`: 存储向量数据库文件
- `src/models/`: 定义 BUG 报告相关的数据模型
- `src/vectorization/`: 实现各类信息的向量化转换
- `src/storage/`: 实现向量数据的存储和检索
- `src/retrieval/`: 实现多向量混合检索策略
- `src/ui/`: 实现用户交互界面

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/bug-knowledge.git
cd bug-knowledge
```

2. 创建虚拟环境（推荐）：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 添加 BUG 报告

```bash
python -m src add-bug
```

按照提示输入以下信息：

- Bug 标题
- 问题描述
- 可复现性
- 重现步骤
- 期望行为
- 实际行为
- 问题代码
- 文件路径
- 代码行号范围
- 编程语言
- 运行时环境
- 操作系统信息
- 网络环境（可选）
- 错误日志

### 搜索 BUG 报告

```bash
python -m src search --query "问题描述" --code "代码片段" --error-log "错误日志" --env-info "环境信息"
```

可选参数：

- `--query`: 问题描述
- `--code`: 代码片段
- `--error-log`: 错误日志
- `--env-info`: 环境信息
- `--n-results`: 返回结果数量（默认为 5）

## 技术架构

系统采用模块化设计，主要包含以下组件：

1. 向量化模块（Vectorization）

   - 问题详情向量化器
   - 代码上下文向量化器
   - 错误日志向量化器
   - 环境信息向量化器

2. 存储模块（Storage）

   - 基于 ChromaDB 的向量存储
   - 支持持久化存储

3. 检索模块（Retrieval）

   - 多向量混合检索
   - 可配置的权重策略

4. 用户界面（UI）
   - 命令行交互界面
   - 格式化输出

## 数据存储

系统使用 ChromaDB 作为向量数据库，数据存储在`data/chroma`目录下。每个 BUG 报告包含以下向量：

- 问题向量：编码问题描述、期望行为和实际行为
- 代码向量：编码问题代码、编程语言和文件路径
- 日志向量：编码错误日志
- 环境向量：编码运行时环境、操作系统和网络环境

## 注意事项

1. 首次运行时会自动下载 sentence-transformers 模型
2. 确保有足够的磁盘空间存储向量数据库
3. 建议定期备份`data/chroma`目录

## 许可证

MIT License
