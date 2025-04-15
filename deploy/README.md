# Bug知识库系统部署指南

## 部署步骤

### 1. 安装依赖

```bash
cd /var/ui/bug-knowledge
pip install -r requirements.txt
```

### 2. 配置Nginx

```bash
# 将Nginx配置文件复制到Nginx配置目录
sudo cp deploy/nginx-bug-knowledge.conf /etc/nginx/sites-available/bug-knowledge.conf
sudo ln -s /etc/nginx/sites-available/bug-knowledge.conf /etc/nginx/sites-enabled/
# 检查配置
sudo nginx -t
# 重新加载Nginx配置
sudo systemctl reload nginx
```

### 3. 配置系统服务

```bash
# 复制服务文件到systemd目录
sudo cp deploy/bug-knowledge.service /etc/systemd/system/
# 重新加载systemd配置
sudo systemctl daemon-reload
# 启用服务
sudo systemctl enable bug-knowledge
# 启动服务
sudo systemctl start bug-knowledge
# 检查服务状态
sudo systemctl status bug-knowledge
```

### 4. 日志查看

```bash
# 查看应用日志
sudo journalctl -u bug-knowledge -f
```

## 常见问题

1. 如果访问网站出现404错误，请检查Nginx配置和FastAPI的root_path设置。
2. 如果静态资源无法加载，请检查Nginx中静态资源的路径配置。
3. 如果服务无法启动，请检查日志排查错误。 