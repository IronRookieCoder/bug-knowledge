#!/bin/bash
# Bug知识库系统部署脚本

# 检查是否以root权限运行
if [ "$(id -u)" != "0" ]; then
   echo "此脚本需要root权限，请使用sudo运行" 
   exit 1
fi

DEPLOY_DIR=$(dirname "$0")
PROJECT_ROOT="/var/ui/bug-knowledge"

echo "=== 开始部署Bug知识库系统 ==="

# 1. 创建必要的目录
echo "创建必要的目录..."
mkdir -p ${PROJECT_ROOT}/data/temp

# 2. 设置权限
echo "设置目录权限..."
chown -R www-data:www-data ${PROJECT_ROOT}
chmod -R 755 ${PROJECT_ROOT}

# 3. 配置Nginx
echo "配置Nginx..."
cp ${DEPLOY_DIR}/nginx-bug-knowledge.conf /etc/nginx/sites-available/bug-knowledge.conf

if [ ! -f /etc/nginx/sites-enabled/bug-knowledge.conf ]; then
    ln -s /etc/nginx/sites-available/bug-knowledge.conf /etc/nginx/sites-enabled/
fi

# 检查Nginx配置
nginx -t
if [ $? -ne 0 ]; then
    echo "Nginx配置有误，请检查配置后重试"
    exit 1
fi

# 重新加载Nginx配置
systemctl reload nginx

# 4. 配置systemd服务
echo "配置系统服务..."
cp ${DEPLOY_DIR}/bug-knowledge.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable bug-knowledge
systemctl restart bug-knowledge

echo "检查服务状态..."
systemctl status bug-knowledge

echo "=== Bug知识库系统部署完成 ==="
echo "访问地址: http://ui.uedc.com/bug-knowledge"
echo "服务日志: journalctl -u bug-knowledge -f" 