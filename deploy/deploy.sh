#!/bin/bash


set -e  # 遇到错误就退出

echo "=========================================="
echo "智能体平台企业级部署开始"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/data/web_new"
DEPLOY_DIR="$PROJECT_ROOT/deploy"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
}

# 安装必要的系统依赖
install_dependencies() {
    log_info "检查并安装系统依赖..."
    
    # 检查nginx是否安装
    if ! command -v nginx &> /dev/null; then
        log_warn "Nginx未安装，正在安装..."
        yum install -y nginx
    else
        log_info "Nginx已安装"
    fi
    
    # 启动并启用nginx
    systemctl enable nginx
    systemctl start nginx
}

# 停止当前服务
stop_current_service() {
    log_info "停止当前运行的服务..."
    
    # 停止可能存在的systemd服务
    if systemctl is-active --quiet intelligent-agent; then
        systemctl stop intelligent-agent
        log_info "已停止systemd服务"
    fi
    
    # 停止直接运行的进程
    pkill -f "python.*run.py" || true
    pkill -f "uvicorn.*9926" || true
    
    sleep 2
}

# 部署systemd服务
deploy_systemd_service() {
    log_info "部署systemd服务..."
    
    # 复制服务文件
    cp "$DEPLOY_DIR/intelligent-agent.service" /etc/systemd/system/
    
    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用并启动服务
    systemctl enable intelligent-agent
    systemctl start intelligent-agent
    
    log_info "Systemd服务部署完成"
}

# 配置nginx
configure_nginx() {
    log_info "配置Nginx反向代理..."
    
    # 备份原有配置
    if [ -f /etc/nginx/conf.d/intelligent-agent.conf ]; then
        cp /etc/nginx/conf.d/intelligent-agent.conf /etc/nginx/conf.d/intelligent-agent.conf.bak.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 复制新配置
    cp "$DEPLOY_DIR/nginx-intelligent-agent.conf" /etc/nginx/conf.d/intelligent-agent.conf
    
    # 测试nginx配置
    if nginx -t; then
        log_info "Nginx配置语法检查通过"
        systemctl reload nginx
        log_info "Nginx配置已重新加载"
    else
        log_error "Nginx配置语法错误"
        exit 1
    fi
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙规则..."
    
    # 开放80端口（HTTP）
    firewall-cmd --permanent --add-port=80/tcp
    # 开放443端口（HTTPS）
    firewall-cmd --permanent --add-port=443/tcp
    # 重新加载防火墙
    firewall-cmd --reload
    
    log_info "防火墙配置完成"
}

# 创建日志轮转配置
setup_log_rotation() {
    log_info "配置日志轮转..."
    
    cat > /etc/logrotate.d/intelligent-agent << EOF
/var/log/nginx/intelligent-agent.*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 nginx nginx
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 \`cat /var/run/nginx.pid\`
        fi
    endscript
}
EOF
    
    log_info "日志轮转配置完成"
}

# 创建监控脚本
create_monitoring() {
    log_info "创建监控脚本..."
    
    cat > /usr/local/bin/check-intelligent-agent.sh << 'EOF'
#!/bin/bash

# 智能体平台健康检查脚本

SERVICE_NAME="intelligent-agent"
HEALTH_URL="http://127.0.0.1:9926/health"
LOG_FILE="/var/log/intelligent-agent-monitor.log"

# 检查systemd服务状态
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): $SERVICE_NAME service is not running, attempting to restart..." >> $LOG_FILE
    systemctl restart $SERVICE_NAME
    sleep 10
fi

# 检查HTTP健康状态
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    echo "$(date): Health check failed (HTTP $HTTP_CODE), restarting service..." >> $LOG_FILE
    systemctl restart $SERVICE_NAME
fi
EOF

    chmod +x /usr/local/bin/check-intelligent-agent.sh
    
    # 添加到crontab（每5分钟检查一次）
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check-intelligent-agent.sh") | crontab -
    
    log_info "监控脚本创建完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."
    
    # 检查服务状态
    if systemctl is-active --quiet intelligent-agent; then
        log_info "✅ Systemd服务运行正常"
    else
        log_error "❌ Systemd服务未运行"
        return 1
    fi
    
    # 检查nginx状态
    if systemctl is-active --quiet nginx; then
        log_info "✅ Nginx服务运行正常"
    else
        log_error "❌ Nginx服务未运行"
        return 1
    fi
    
    # 检查端口监听
    if netstat -tlnp | grep -q ":9926.*LISTEN"; then
        log_info "✅ 应用端口9926监听正常"
    else
        log_error "❌ 应用端口9926未监听"
        return 1
    fi
    
    # 检查HTTP响应
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        log_info "✅ HTTP健康检查通过"
    else
        log_error "❌ HTTP健康检查失败 (HTTP $HTTP_CODE)"
        return 1
    fi
    
    log_info "部署验证完成！"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "=========================================="
    echo "📋 部署完成信息"
    echo "=========================================="
    echo "🌐 访问地址: http://36.138.75.130"
    echo "🔧 管理命令:"
    echo "   启动服务: systemctl start intelligent-agent"
    echo "   停止服务: systemctl stop intelligent-agent"
    echo "   重启服务: systemctl restart intelligent-agent"
    echo "   查看状态: systemctl status intelligent-agent"
    echo "   查看日志: journalctl -u intelligent-agent -f"
    echo ""
    echo "📊 监控信息:"
    echo "   健康检查: curl http://127.0.0.1/health"
    echo "   监控日志: tail -f /var/log/intelligent-agent-monitor.log"
    echo "   Nginx日志: tail -f /var/log/nginx/intelligent-agent.access.log"
    echo ""
    echo "🔐 账户信息:"
    echo "   管理员: admin / admin123"
    echo "   测试用户: test / test123"
    echo "=========================================="
}

# 主函数
main() {
    check_root
    
    cd "$PROJECT_ROOT"
    
    log_info "开始企业级部署..."
    
    install_dependencies
    stop_current_service
    deploy_systemd_service
    configure_nginx
    configure_firewall
    setup_log_rotation
    create_monitoring
    
    sleep 5  # 等待服务完全启动
    
    if verify_deployment; then
        show_deployment_info
        log_info "🎉 企业级部署成功完成！"
    else
        log_error "❌ 部署验证失败，请检查错误信息"
        exit 1
    fi
}

# 执行主函数
main "$@" 