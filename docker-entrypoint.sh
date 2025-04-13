#!/bin/bash

# 激活虚拟环境
source /app/venv/bin/activate

# 设置默认参数
MODE=${MODE:-"web"}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8010"}
SCHEDULE=${SCHEDULE:-""}
HOUR=${HOUR:-"2"}
MINUTE=${MINUTE:-"0"}
INTERVAL=${INTERVAL:-"24"}
ENV=${PYTHON_ENV:-"production"}

# 检测Python命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Neither python3 nor python command found"
    exit 1
fi

# 构建启动命令
if [ -n "$SCHEDULE" ]; then
    if [ -n "$INTERVAL" ]; then
        CMD="$PYTHON_CMD -m src --mode $MODE --host $HOST --port $PORT --schedule --interval $INTERVAL"
    else
        CMD="$PYTHON_CMD -m src --mode $MODE --host $HOST --port $PORT --schedule --hour $HOUR --minute $MINUTE"
    fi
else
    CMD="$PYTHON_CMD -m src --mode $MODE --host $HOST --port $PORT"
fi

# 执行命令
echo "Starting with command: $CMD"
exec $CMD