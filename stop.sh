#!/bin/bash

# 错误处理
set -e

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 输出帮助信息
show_help() {
    echo "Bug知识库系统停止脚本"
    echo "用法: ./stop.sh [选项]"
    echo "选项:"
    echo "  -f, --force     强制停止进程"
    echo "  -c, --clean     停止后清理临时文件"
    echo "  -h, --help      显示此帮助信息"
}

# 默认参数
FORCE=0
CLEAN=0

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=1
            shift
            ;;
        -c|--clean)
            CLEAN=1
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}错误：未知选项 $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 在Windows下查找Python进程
find_bug_knowledge_processes() {
    # 同时查找 python.exe 和 python3.exe
    (cmd.exe /c "tasklist /FI \"IMAGENAME eq python.exe\" /FO CSV /NH" 2>/dev/null && \
     cmd.exe /c "tasklist /FI \"IMAGENAME eq python3.exe\" /FO CSV /NH" 2>/dev/null) | \
    grep -i "python" | \
    while IFS=',' read -r name pid rest; do
        # 提取PID，去除引号
        pid=$(echo "$pid" | tr -d '"')
        # 检查命令行参数是否包含 "src"
        if cmd.exe /c "wmic process where ProcessId=$pid get CommandLine" 2>/dev/null | grep -q "src"; then
            echo "$pid"
        fi
    done
}

# 获取进程列表
PIDS=$(find_bug_knowledge_processes)

if [ -z "$PIDS" ]; then
    echo -e "${YELLOW}没有找到运行中的 bug-knowledge 进程${NC}"
    exit 0
fi

# 显示找到的进程
echo -e "${GREEN}找到以下运行中的进程：${NC}"
for pid in $PIDS; do
    cmd.exe /c "wmic process where ProcessId=$pid get ProcessId,CommandLine"
done

# 确认停止操作
if [ "$FORCE" -ne 1 ]; then
    echo -e "${YELLOW}确认要停止这些进程吗? [y/N]${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "操作已取消"
        exit 0
    fi
fi

# 停止进程函数
stop_process() {
    local pid=$1
    local force=$2
    
    if [ "$force" -eq 1 ]; then
        echo -e "${YELLOW}正在强制停止进程 $pid...${NC}"
        cmd.exe /c "taskkill /F /PID $pid" 2>/dev/null || true
    else
        echo -e "${GREEN}正在优雅停止进程 $pid...${NC}"
        cmd.exe /c "taskkill /PID $pid" 2>/dev/null || true
        
        # 等待进程退出
        local count=0
        while cmd.exe /c "tasklist /FI \"PID eq $pid\"" 2>/dev/null | grep -q "$pid"; do
            sleep 1
            count=$((count + 1))
            if [ $count -ge 10 ]; then
                echo -e "${YELLOW}进程 $pid 没有响应，正在强制停止...${NC}"
                cmd.exe /c "taskkill /F /PID $pid" 2>/dev/null || true
                break
            fi
        done
    fi
}

# 停止所有进程
for pid in $PIDS; do
    stop_process "$pid" "$FORCE"
done

# 验证所有进程都已停止
sleep 2
REMAINING_PIDS=$(find_bug_knowledge_processes)
if [ -n "$REMAINING_PIDS" ]; then
    echo -e "${RED}警告：以下进程仍在运行：${NC}"
    for pid in $REMAINING_PIDS; do
        cmd.exe /c "wmic process where ProcessId=$pid get ProcessId,CommandLine"
    done
    echo -e "${RED}请使用 -f 选项强制停止这些进程${NC}"
    exit 1
fi

# 清理临时文件
if [ "$CLEAN" -eq 1 ]; then
    echo -e "${GREEN}正在清理临时文件...${NC}"
    rm -rf data/temp/* 2>/dev/null || true
    echo -e "${GREEN}临时文件已清理${NC}"
fi

echo -e "${GREEN}所有进程已停止${NC}"