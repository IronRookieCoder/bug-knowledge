#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 错误处理函数
handle_error() {
    echo -e "${RED}错误: $1${NC}"
    exit 1
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        handle_error "未安装 $1"
    fi
}

# 安装Python 3.8
install_python() {
    echo -e "${GREEN}1. 安装Python 3.8...${NC}"
    cd python
    
    # 检查Python安装包
    if [ ! -f "Python-3.8.0.tgz" ]; then
        handle_error "未找到Python安装包"
    fi
    
    # 解压并安装
    tar -xzf Python-3.8.0.tgz || handle_error "解压Python安装包失败"
    cd Python-3.8.0
    
    # 配置和编译
    ./configure --prefix=/usr/local/python3.8 || handle_error "Python配置失败"
    make || handle_error "Python编译失败"
    make install || handle_error "Python安装失败"
    
    # 创建软链接
    ln -sf /usr/local/python3.8/bin/python3.8 /usr/bin/python3
    ln -sf /usr/local/python3.8/bin/pip3 /usr/bin/pip3
    
    cd ../..
}

# 安装系统依赖
install_system_deps() {
    echo -e "${GREEN}2. 安装系统依赖...${NC}"
    cd rpms
    
    # 检查rpm包
    if [ ! "$(ls -A *.rpm 2>/dev/null)" ]; then
        handle_error "未找到系统依赖包"
    fi
    
    # 安装依赖
    yum localinstall -y *.rpm || handle_error "安装系统依赖失败"
    
    cd ..
}

# 配置环境
configure_environment() {
    echo -e "${GREEN}3. 配置环境...${NC}"
    
    # 配置Docker服务自启动
    systemctl enable docker || echo -e "${YELLOW}警告: 无法设置Docker服务自启动${NC}"
    
    # 安装curl（如果不存在）
    if ! command -v curl &> /dev/null; then
        echo -e "${YELLOW}安装curl...${NC}"
        yum install -y curl || echo -e "${YELLOW}警告: 无法安装curl，部署验证可能会失败${NC}"
    fi
    
    # 配置防火墙
    if command -v firewall-cmd &> /dev/null; then
        echo -e "${YELLOW}配置防火墙...${NC}"
        firewall-cmd --permanent --add-port=8010/tcp || handle_error "配置防火墙失败"
        firewall-cmd --reload || handle_error "重新加载防火墙失败"
    else
        echo -e "${YELLOW}未安装firewall-cmd，跳过防火墙配置${NC}"
    fi
    
    # 配置SELinux
    if command -v setenforce &> /dev/null; then
        echo -e "${YELLOW}配置SELinux...${NC}"
        setenforce 0 || handle_error "临时关闭SELinux失败"
        sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config || handle_error "永久关闭SELinux失败"
    else
        echo -e "${YELLOW}未安装SELinux，跳过SELinux配置${NC}"
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -h /var/lib/docker | awk 'NR==2 {print $4}')
    echo -e "${YELLOW}Docker数据目录可用空间: ${AVAILABLE_SPACE}${NC}"
    
    # 检查内存空间
    AVAILABLE_MEM=$(free -h | awk 'NR==2 {print $7}')
    echo -e "${YELLOW}系统可用内存: ${AVAILABLE_MEM}${NC}"
}

# 恢复数据
restore_data() {
    echo -e "${GREEN}4. 恢复数据...${NC}"
    
    if [ -f "data/data.tar.gz" ]; then
        echo -e "${YELLOW}发现数据备份，开始恢复...${NC}"
        docker run --rm -v bug-knowledge:/target -v $(pwd)/data:/backup \
            alpine sh -c "cd /target && tar -xzf /backup/data.tar.gz" || handle_error "数据恢复失败"
    else
        echo -e "${YELLOW}未发现数据备份，跳过数据恢复${NC}"
    fi
}

# 构建和启动容器
deploy_containers() {
    echo -e "${GREEN}5. 构建Docker镜像...${NC}"
    docker build -t bug-knowledge:offline . || handle_error "构建Docker镜像失败"
    
    echo -e "${GREEN}6. 启动容器...${NC}"
    docker-compose up -d || handle_error "启动容器失败"
}

# 验证部署
verify_deployment() {
    echo -e "${GREEN}7. 验证部署...${NC}"
    
    # 检查容器状态
    if ! docker-compose ps | grep -q "Up"; then
        handle_error "容器未正常运行"
    fi
    
    # 等待服务启动
    echo -e "${YELLOW}等待服务启动...${NC}"
    sleep 10
    
    # 检查应用是否可访问
    if ! curl -s --connect-timeout 5 http://localhost:8010 > /dev/null; then
        echo -e "${YELLOW}警告: 应用可能未完全启动，请稍后重试访问 http://localhost:8010${NC}"
    else
        echo -e "${GREEN}应用已成功启动并可访问${NC}"
    fi
}

# 主函数
main() {
    # 检查是否以root权限运行
    if [ "$EUID" -ne 0 ]; then 
        handle_error "请使用root权限运行此脚本"
    fi
    
    echo -e "${GREEN}开始离线部署...${NC}"
    
    # 检查必要的命令
    check_command docker
    check_command docker-compose
    
    # 解压部署包
    if [ -f "bug-knowledge-offline.tar.gz" ]; then
        echo -e "${GREEN}解压部署包...${NC}"
        tar -xzf bug-knowledge-offline.tar.gz || handle_error "解压部署包失败"
    else
        handle_error "未找到部署包 bug-knowledge-offline.tar.gz"
    fi
    
    # 进入部署目录
    cd deployment
    
    # 执行部署步骤
    install_python
    install_system_deps
    configure_environment
    restore_data
    deploy_containers
    verify_deployment
    
    echo -e "${GREEN}部署完成！${NC}"
    echo -e "应用运行在: ${GREEN}http://localhost:8010${NC}"
    echo -e "查看容器状态: ${GREEN}docker-compose ps${NC}"
    echo -e "查看容器日志: ${GREEN}docker-compose logs -f${NC}"
}

# 执行主函数
main 