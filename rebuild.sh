#!/bin/bash
# 删除旧环境
rm -rf venv/
# 创建新环境
python -m venv venv
# 激活环境并安装依赖
source venv/bin/activate && pip install -r requirements.txt