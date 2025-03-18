#!/bin/bash
# 删除旧环境
rm -rf venv/
# 创建新环境
python -m venv venv
# 激活环境并安装依赖
source venv/Scripts/activate
# 升级pip
# 使用清华源加速下载（避免超时）
python -m pip install --cache-dir=./pip_cache --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simplepip install --upgrade pip
# 安装依赖
pip install -r requirements.txt