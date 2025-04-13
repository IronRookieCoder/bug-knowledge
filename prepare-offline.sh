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

# 准备Python 3.8离线包
prepare_python() {
    echo -e "${GREEN}1. 准备Python 3.8离线安装包...${NC}"
    mkdir -p "${DEPLOY_DIR}/python"
    cd "${DEPLOY_DIR}/python"
    
    # 下载Python 3.8
    wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz || handle_error "下载Python失败"
    wget https://www.python.org/ftp/python/3.8.0/Python-3.8.0.tgz.asc || handle_error "下载Python签名失败"
    
    # 验证下载文件
    if [ ! -f "Python-3.8.0.tgz" ] || [ ! -f "Python-3.8.0.tgz.asc" ]; then
        handle_error "Python安装包下载不完整"
    fi
    
    cd - > /dev/null
}

# 准备系统依赖包
prepare_system_deps() {
    echo -e "${GREEN}2. 准备系统依赖包...${NC}"
    mkdir -p "${DEPLOY_DIR}/rpms"
    
    # 下载系统依赖
    yum install --downloadonly --downloaddir="${DEPLOY_DIR}/rpms" \
        yum-utils device-mapper-persistent-data lvm2 curl || handle_error "下载系统依赖失败"
    
    # 检查下载的rpm包
    if [ ! "$(ls -A ${DEPLOY_DIR}/rpms/*.rpm 2>/dev/null)" ]; then
        handle_error "系统依赖包下载失败"
    fi
}

# 准备Python依赖包
prepare_python_deps() {
    echo -e "${GREEN}3. 准备Python依赖包...${NC}"
    mkdir -p "${DEPLOY_DIR}/packages"
    
    # 下载Python依赖
    pip download -r requirements.txt -d "${DEPLOY_DIR}/packages" || handle_error "下载Python依赖失败"
    
    # 检查下载的包
    if [ ! "$(ls -A ${DEPLOY_DIR}/packages/* 2>/dev/null)" ]; then
        handle_error "Python依赖包下载失败"
    fi
}

# 备份数据
backup_data() {
    echo -e "${GREEN}4. 备份数据...${NC}"
    mkdir -p "${DEPLOY_DIR}/data"
    
    # 检查是否有数据卷
    if docker volume ls | grep -q "bug-knowledge"; then
        echo -e "${YELLOW}发现数据卷，开始备份...${NC}"
        docker run --rm -v bug-knowledge:/source -v $(pwd)/${DEPLOY_DIR}/data:/backup \
            alpine tar -czf /backup/data.tar.gz -C /source . || handle_error "数据备份失败"
    else
        echo -e "${YELLOW}未发现数据卷，跳过数据备份${NC}"
    fi
}

# 复制项目文件
copy_project_files() {
    echo -e "${GREEN}5. 复制项目文件...${NC}"
    # 复制必要的文件到部署目录
    cp Dockerfile "${DEPLOY_DIR}/" || handle_error "复制Dockerfile失败"
    cp docker-compose.yml "${DEPLOY_DIR}/" || handle_error "复制docker-compose.yml失败"
    cp docker-entrypoint.sh "${DEPLOY_DIR}/" || handle_error "复制docker-entrypoint.sh失败"
    cp requirements.txt "${DEPLOY_DIR}/" || handle_error "复制requirements.txt失败"
    cp -r src "${DEPLOY_DIR}/" || handle_error "复制src目录失败"
    
    # 添加备份
    cp docker-compose.yml "${DEPLOY_DIR}/docker-compose.yml.bak" || handle_error "备份docker-compose.yml失败"
}

# 创建部署说明文件
create_readme() {
    echo -e "${GREEN}6. 创建部署说明文件...${NC}"
    cat > "${DEPLOY_DIR}/README.md" << EOF
# 离线部署说明

## 部署步骤

1. 确保目标服务器已安装：
   - Docker
   - Docker Compose
   - Python 3.8

2. 将整个deployment目录复制到目标服务器

3. 在目标服务器上执行：
   \`\`\`bash
   cd deployment
   docker build -t bug-knowledge:offline .
   docker-compose up -d
   \`\`\`

## 环境变量配置

可以通过修改docker-compose.yml文件中的环境变量来配置应用：

- MODE: 运行模式 (web/schedule)
- HOST: 监听地址
- PORT: 监听端口
- SCHEDULE: 是否启用定时任务
- HOUR: 定时任务小时
- MINUTE: 定时任务分钟
- INTERVAL: 定时任务间隔（小时）

## 数据恢复

如果包含数据备份，可以使用以下命令恢复数据：

\`\`\`bash
docker run --rm -v bug-knowledge:/target -v \$(pwd)/data:/backup \\
    alpine sh -c "cd /target && tar -xzf /backup/data.tar.gz"
\`\`\`
EOF
}

# 打包部署文件
package_deployment() {
    echo -e "${GREEN}7. 打包部署文件...${NC}"
    tar -czf bug-knowledge-offline.tar.gz "${DEPLOY_DIR}" || handle_error "打包部署文件失败"
}

# 主函数
main() {
    echo -e "${GREEN}开始准备离线部署包...${NC}"
    
    # 检查必要的命令
    check_command docker
    check_command pip
    check_command wget
    check_command yum
    check_command curl
    
    # 创建部署目录
    DEPLOY_DIR="deployment"
    rm -rf "${DEPLOY_DIR}"
    mkdir -p "${DEPLOY_DIR}"
    
    # 执行准备步骤
    prepare_python
    prepare_system_deps
    prepare_python_deps
    backup_data
    copy_project_files
    create_readme
    package_deployment
    
    echo -e "${GREEN}部署包准备完成！${NC}"
    echo -e "部署包位置: ${GREEN}$(pwd)/bug-knowledge-offline.tar.gz${NC}"
    echo -e "部署说明: ${GREEN}$(pwd)/${DEPLOY_DIR}/README.md${NC}"
}

# 执行主函数
main 