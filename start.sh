#!/bin/bash

# 检查是否安装了Python
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 python，请先安装 python"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# 安装依赖
if [ ! -f "venv/installed" ]; then
    echo "安装项目依赖..."
    pip install -r requirements.txt
    touch venv/installed
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
    echo "  --help         显示此帮助信息"
}

# 默认参数
MODE=""
HOST="127.0.0.1"
PORT="8010"
SCHEDULE=""
HOUR="--hour 2"
MINUTE="--minute 0"
INTERVAL="--interval 24"

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
            HOUR="--hour $2"
            shift 2
            ;;
        --minute)
            MINUTE="--minute $2"
            shift 2
            ;;
        --interval)
            INTERVAL="--interval $2"
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

# 检查必需参数
if [ -z "$MODE" ]; then
    echo "错误: 必须指定运行模式 (-m|--mode)"
    show_help
    exit 1
fi

# 构建启动命令
if [ -n "$SCHEDULE" ]; then
    # 如果启用了计划任务，且没有指定interval，则使用hour和minute
    if [[ "$@" != *"--interval"* ]]; then
        CMD="python -m src --mode $MODE --host $HOST --port $PORT $SCHEDULE $HOUR $MINUTE"
    else
        CMD="python -m src --mode $MODE --host $HOST --port $PORT $SCHEDULE $INTERVAL"
    fi
else
    CMD="python -m src --mode $MODE --host $HOST --port $PORT"
fi

# 执行命令
echo "启动命令: $CMD"
exec $CMD