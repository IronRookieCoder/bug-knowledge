#!/bin/bash
# 删除旧环境
rm -rf venv/
# 创建新环境
python -m venv venv
# 激活环境
source venv/Scripts/activate
# 安装依赖
pip install -r requirements.txt