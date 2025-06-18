# 智能体平台企业级部署方案

## 🚀 概述

本文档提供了智能体平台的多种企业级部署方案，确保服务可以稳定、持续运行。

## 📋 部署方案对比

| 特性 | Systemd + Nginx | Docker Compose | Kubernetes |
|------|----------------|----------------|------------|
| 复杂度 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 资源使用 | 低 | 中等 | 中等 |
| 伸缩性 | 有限 | 中等 | 高 |
| 运维难度 | 低 | 中等 | 高 |
| 适用场景 | 单机部署 | 开发/测试/小规模生产 | 大规模生产 |

## 🔧 方案一：Systemd + Nginx (推荐)

### 特点
- ✅ 企业级稳定性
- ✅ 自动重启和故障恢复
- ✅ 系统级服务管理
- ✅ 完整的日志管理
- ✅ Nginx反向代理
- ✅ 自动化监控

### 部署步骤

1. **一键部署**
   ```bash
   cd /data/web_new
   sudo ./deploy/deploy.sh
   ```

2. **手动部署**
   ```bash
   # 复制服务文件
   sudo cp deploy/intelligent-agent.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable intelligent-agent
   sudo systemctl start intelligent-agent
   
   # 配置Nginx
   sudo cp deploy/nginx-intelligent-agent.conf /etc/nginx/conf.d/
   sudo nginx -t && sudo systemctl reload nginx
   
   # 配置防火墙
   sudo firewall-cmd --permanent --add-port=80/tcp
   sudo firewall-cmd --permanent --add-port=443/tcp
   sudo firewall-cmd --reload
   ```

### 管理命令

```bash
# 启动/停止/重启服务
sudo systemctl start intelligent-agent
sudo systemctl stop intelligent-agent
sudo systemctl restart intelligent-agent

# 查看服务状态
sudo systemctl status intelligent-agent

# 查看日志
sudo journalctl -u intelligent-agent -f

# 使用管理脚本
./deploy/manage.sh status
./deploy/manage.sh restart
./deploy/manage.sh health
```

## 🐳 方案二：Docker Compose

### 特点
- ✅ 容器化部署
- ✅ 环境隔离
- ✅ 一键启停
- ✅ 包含Redis缓存
- ✅ 可选监控服务
- ✅ 数据持久化

### 部署步骤

1. **构建并启动**
   ```bash
   cd /data/web_new
   docker-compose up -d
   ```

2. **启动包含监控**
   ```bash
   docker-compose --profile monitoring up -d
   ```

### 管理命令

```bash
# 启动/停止
docker-compose up -d
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f intelligent-agent

# 重新构建
docker-compose build --no-cache

# 使用管理脚本
./deploy/manage.sh status
./deploy/manage.sh build
```

## 🛠️ 管理脚本使用

项目提供了统一的管理脚本 `deploy/manage.sh`，支持两种部署方式：

```bash
# 查看帮助
./deploy/manage.sh help

# 服务管理
./deploy/manage.sh start      # 启动服务
./deploy/manage.sh stop       # 停止服务
./deploy/manage.sh restart    # 重启服务
./deploy/manage.sh status     # 查看状态

# 运维功能
./deploy/manage.sh health     # 健康检查
./deploy/manage.sh logs       # 查看日志
./deploy/manage.sh backup     # 备份数据
./deploy/manage.sh update     # 更新应用
```

## 📊 监控和日志

### 系统监控
- **健康检查**: `curl http://127.0.0.1/health`
- **服务状态**: `./deploy/manage.sh health`
- **系统资源**: 内存、磁盘使用情况

### 日志管理
- **应用日志**: `/var/log/nginx/intelligent-agent.*.log`
- **系统日志**: `journalctl -u intelligent-agent`
- **监控日志**: `/var/log/intelligent-agent-monitor.log`

### 自动监控
- 每5分钟自动健康检查
- 服务异常自动重启
- 日志自动轮转（保留52天）

## 🔒 安全配置

### 防火墙设置
```bash
# 开放必要端口
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

### Nginx安全头
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Content-Security-Policy

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 查看详细错误
   journalctl -u intelligent-agent -n 50
   
   # 检查端口占用
   netstat -tlnp | grep :9926
   ```

2. **Nginx配置错误**
   ```bash
   # 测试配置
   nginx -t
   
   # 重新加载配置
   systemctl reload nginx
   ```

3. **权限问题**
   ```bash
   # 检查文件权限
   ls -la /data/web_new
   
   # 修复权限
   chown -R root:root /data/web_new
   ```

### 应急恢复

1. **服务重启**
   ```bash
   ./deploy/manage.sh restart
   ```

2. **从备份恢复**
   ```bash
   # 查看可用备份
   ls -la /data/backups/
   
   # 恢复数据
   cp -r /data/backups/YYYYMMDD_HHMMSS/data /data/web_new/
   ```

## 📈 性能优化

### 系统级优化
```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化内核参数
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
sysctl -p
```

### 应用级优化
- 启用Nginx缓存
- 配置数据库连接池
- 使用Redis缓存
- 启用gzip压缩

## 🔄 更新和维护

### 定期维护任务
```bash
# 每日备份
0 2 * * * /data/web_new/deploy/manage.sh backup

# 每周健康检查报告
0 8 * * 1 /data/web_new/deploy/manage.sh health > /var/log/weekly-health.log

# 每月日志清理
0 3 1 * * find /var/log/nginx -name "*.log" -mtime +30 -delete
```

### 版本更新
```bash
# 停止服务
./deploy/manage.sh stop

# 备份当前版本
./deploy/manage.sh backup

# 更新代码（Git pull 或者文件替换）
git pull origin main

# 启动服务
./deploy/manage.sh start

# 验证更新
./deploy/manage.sh health
```

## 📞 技术支持

### 联系信息
- 平台管理员: admin@example.com
- 技术支持: tech-support@example.com

### 紧急联系
- 24/7 技术热线: 400-XXX-XXXX
- 应急响应: emergency@example.com

---

## 🎯 快速开始

如果您是第一次部署，推荐使用 **Systemd + Nginx** 方案：

```bash
# 1. 克隆或下载项目到 /data/web_new
# 2. 执行一键部署
cd /data/web_new
sudo ./deploy/deploy.sh

# 3. 验证部署
./deploy/manage.sh health

# 4. 访问系统
curl http://YOUR_SERVER_IP/auth/login
```

🎉 **恭喜！您的智能体平台已成功部署并可以稳定运行！** 