#!/bin/bash

# 错误处理
set -e

echo "Removing existing environment..."
conda remove --name bug-knowledge --all -y 2>/dev/null || true

echo "Rebuilding environment..."
./setup

echo "Environment rebuild complete!"