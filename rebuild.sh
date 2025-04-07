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

echo "开始重建环境..."

# 删除旧环境
echo "删除现有环境..."
conda remove --name bug-knowledge --all -y 2>/dev/null || true

# 创建新环境
echo "创建新环境..."
conda env create -f environment.yml

echo "环境重建完成！"