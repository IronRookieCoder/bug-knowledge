#!/bin/bash

# 错误处理
set -e

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
    echo "重建知识库索引脚本"
    echo "用法: ./rebuild.sh [选项]"
    echo "选项:"
    echo "  -h, --help      显示此帮助信息"
}

# 默认参数
ENV=${PYTHON_ENV:-"production"}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
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

# 设置环境变量
export PYTHON_ENV=$ENV

# 获取当前目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 备份并重建
echo "开始重建索引..."
$PYTHON_CMD -m src --mode storage --rebuild
echo "重建完成！"