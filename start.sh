#!/bin/bash

# 错误处理
set -e

# 通用变量
ENV_NAME="bug-knowledge"

# 检测Python命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Neither python3 nor python command found"
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
SCHEDULE=${SCHEDULE:-"--schedule"}
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
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查模式是否有效
case $MODE in
    crawler|storage|web|all)
        ;;
    *)
        echo "Error: Invalid mode '$MODE'"
        show_help
        exit 1
        ;;
esac

# 设置环境变量
export PYTHON_ENV=$ENV

# 构建启动命令
if [ -n "$SCHEDULE" ]; then
    # 如果启用了计划任务，且没有指定interval，则使用hour和minute
    if [[ "$@" != *"--interval"* ]]; then
        CMD="$PYTHON_CMD -m src --mode $MODE --host $HOST --port $PORT $SCHEDULE --hour $HOUR --minute $MINUTE"
    else
        CMD="$PYTHON_CMD -m src --mode $MODE --host $HOST --port $PORT $SCHEDULE --interval $INTERVAL"
    fi
else
    CMD="$PYTHON_CMD -m src --mode $MODE --host $HOST --port $PORT"
fi

# 执行命令
echo "Starting command: $CMD"
exec $CMD