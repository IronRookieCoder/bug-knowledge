#!/bin/bash

# 错误处理
set -e

# 检查操作系统类型
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows环境下的conda路径处理
    if [[ -z "${CONDA_PATH}" ]]; then
        # 尝试常见的conda安装路径
        if [ -d "/c/Users/$USER/miniconda3" ]; then
            CONDA_PATH="/c/Users/$USER/miniconda3"
        elif [ -d "/c/Users/$USER/Anaconda3" ]; then
            CONDA_PATH="/c/Users/$USER/Anaconda3"
        elif [ -d "/d/conda" ]; then
            CONDA_PATH="/d/conda"
        else
            echo "错误: 未找到conda安装路径，请设置CONDA_PATH环境变量"
            exit 1
        fi
    fi
    source "${CONDA_PATH}/etc/profile.d/conda.sh"
fi

# 检查conda是否安装
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到 conda，请先安装 Miniconda 或 Anaconda"
    exit 1
fi

# 加载 .env 文件（如果存在）
if [ -f ".env" ]; then
    echo "加载 .env 配置文件..."
    set -a
    source .env
    set +a
fi

# 激活或创建conda环境
if ! conda activate bug-knowledge 2>/dev/null; then
    echo "创建conda环境..."
    conda env create -f environment.yml
    conda activate bug-knowledge
fi

# 检查Python版本
python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version < 3.8" | bc -l) )); then
    echo "错误: 需要 Python 3.8 或更高版本"
    echo "当前版本: $python_version"
    exit 1
fi

# 定义帮助信息
show_help() {
    echo "Bug知识库系统启动脚本"
    echo "用法: ./start.sh [选项]"
    echo "选项:"
    echo "  -m, --mode       运行模式: crawler|storage|web|all (必需)"
    echo "  -h, --host      Web服务器主机地址 (默认: 127.0.0.1)"
    echo "  -p, --port      Web服务器端口 (默认: 8010)"
    echo "  -s, --schedule  启用计划运行模式"
    echo "  --hour         计划任务执行的小时 (0-23, 默认: 2)"
    echo "  --minute       计划任务执行的分钟 (0-59, 默认: 0)"
    echo "  --interval     任务执行的间隔时间（小时，默认: 24）"
    echo "  --env          运行环境: development|production"
    echo "  --help         显示此帮助信息"
}

# 默认参数（优先使用环境变量中的值）
MODE=${MODE:-"web"}
HOST=${HOST:-"127.0.0.1"}
PORT=${PORT:-"8010"}
SCHEDULE=${SCHEDULE:-""}
HOUR=${HOUR:-"2"}
MINUTE=${MINUTE:-"0"}
INTERVAL=${INTERVAL:-"24"}
ENV=${PYTHON_ENV:-"production"}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -s|--schedule)
            SCHEDULE="--schedule"
            shift
            ;;
        --hour)
            HOUR="$2"
            shift 2
            ;;
        --minute)
            MINUTE="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --env)
            ENV="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 创建必要的目录
mkdir -p logs data/annoy

# 设置环境变量
export PYTHON_ENV=$ENV

# 检查模式是否有效
case $MODE in
    crawler|storage|web|all)
        ;;
    *)
        echo "错误: 无效的运行模式 '$MODE'"
        show_help
        exit 1
        ;;
esac

# 构建启动命令
if [ -n "$SCHEDULE" ]; then
    # 如果启用了计划任务，且没有指定interval，则使用hour和minute
    if [[ "$@" != *"--interval"* ]]; then
        CMD="python -m src --mode $MODE --host $HOST --port $PORT $SCHEDULE --hour $HOUR --minute $MINUTE"
    else
        CMD="python -m src --mode $MODE --host $HOST --port $PORT $SCHEDULE --interval $INTERVAL"
    fi
else
    CMD="python -m src --mode $MODE --host $HOST --port $PORT"
fi

# 执行命令
echo "启动命令: $CMD"
exec $CMD