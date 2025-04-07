#!/bin/bash

# 激活conda环境
source ~/.bashrc

# 设置默认参数
MODE=${MODE:-"web"}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8010"}
SCHEDULE=${SCHEDULE:-""}
HOUR=${HOUR:-"2"}
MINUTE=${MINUTE:-"0"}
INTERVAL=${INTERVAL:-"24"}
ENV=${PYTHON_ENV:-"production"}

# 构建启动命令
if [ -n "$SCHEDULE" ]; then
    if [ -n "$INTERVAL" ]; then
        CMD="python -m src --mode $MODE --host $HOST --port $PORT --schedule --interval $INTERVAL"
    else
        CMD="python -m src --mode $MODE --host $HOST --port $PORT --schedule --hour $HOUR --minute $MINUTE"
    fi
else
    CMD="python -m src --mode $MODE --host $HOST --port $PORT"
fi

# 执行命令
echo "Starting with command: $CMD"
exec $CMD