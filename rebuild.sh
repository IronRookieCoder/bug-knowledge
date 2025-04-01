#!/bin/bash

# 错误处理
set -e

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python3"
    exit 1
fi

# 检查Python版本号
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version < 3.8" | bc -l) )); then
    echo "错误: 需要 Python 3.8 或更高版本"
    echo "当前版本: $python_version"
    exit 1
fi

echo "开始重建环境..."

# 删除旧环境
if [ -d "venv" ]; then
    echo "删除旧虚拟环境..."
    rm -rf venv/
fi

# 创建新环境
echo "创建新虚拟环境..."
python3 -m venv venv || {
    echo "创建虚拟环境失败"
    exit 1
}

# 激活环境
echo "激活虚拟环境..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate || {
        echo "激活虚拟环境失败"
        exit 1
    }
else
    source venv/bin/activate || {
        echo "激活虚拟环境失败"
        exit 1
    }
fi

# 升级pip
echo "升级pip..."
python -m pip install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
pip install -r requirements.txt || {
    echo "安装依赖失败"
    exit 1
}

# 创建安装标记
touch venv/installed

echo "环境重建完成！"