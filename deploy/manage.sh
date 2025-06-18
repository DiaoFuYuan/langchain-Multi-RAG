#!/bin/bash

# 智能体平台管理脚本
# 支持 systemd 和 docker 两种部署方式

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="/data/web_new"

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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检测部署类型
detect_deployment_type() {
    if systemctl is-active --quiet intelligent-agent 2>/dev/null; then
        echo "systemd"
    elif docker ps --filter "name=intelligent-agent-app" --format "table {{.Names}}" | grep -q intelligent-agent-app; then
        echo "docker"
    else
        echo "none"
    fi
}

# Systemd 管理函数
systemd_start() {
    log_info "启动 Systemd 服务..."
    systemctl start intelligent-agent
    systemctl start nginx
}

systemd_stop() {
    log_info "停止 Systemd 服务..."
    systemctl stop intelligent-agent
}

systemd_restart() {
    log_info "重启 Systemd 服务..."
    systemctl restart intelligent-agent
    systemctl reload nginx
}

systemd_status() {
    echo "=== Systemd 服务状态 ==="
    systemctl status intelligent-agent --no-pager -l
    echo ""
    systemctl status nginx --no-pager
}

systemd_logs() {
    log_info "查看 Systemd 服务日志..."
    journalctl -u intelligent-agent -f
}

# Docker 管理函数
docker_start() {
    log_info "启动 Docker 容器..."
    cd "$PROJECT_ROOT"
    docker-compose up -d
}

docker_stop() {
    log_info "停止 Docker 容器..."
    cd "$PROJECT_ROOT"
    docker-compose down
}

docker_restart() {
    log_info "重启 Docker 容器..."
    cd "$PROJECT_ROOT"
    docker-compose restart
}

docker_status() {
    echo "=== Docker 容器状态 ==="
    cd "$PROJECT_ROOT"
    docker-compose ps
}

docker_logs() {
    log_info "查看 Docker 容器日志..."
    cd "$PROJECT_ROOT"
    docker-compose logs -f intelligent-agent
}

docker_build() {
    log_info "构建 Docker 镜像..."
    cd "$PROJECT_ROOT"
    docker-compose build --no-cache
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local deployment_type=$(detect_deployment_type)
    
    echo "部署类型: $deployment_type"
    echo ""
    
    # 检查端口监听
    if netstat -tlnp | grep -q ":80.*LISTEN"; then
        log_info "✅ Nginx (80端口) 正常监听"
    else
        log_warn "❌ Nginx (80端口) 未监听"
    fi
    
    if netstat -tlnp | grep -q ":9926.*LISTEN"; then
        log_info "✅ 应用服务 (9926端口) 正常监听"
    else
        log_warn "❌ 应用服务 (9926端口) 未监听"
    fi
    
    # HTTP健康检查
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health 2>/dev/null || echo "000")
    if [ "$http_code" = "200" ]; then
        log_info "✅ HTTP健康检查通过 ($http_code)"
    else
        log_warn "❌ HTTP健康检查失败 ($http_code)"
    fi
    
    # 内存使用情况
    local memory_usage=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
    log_info "📊 内存使用: $memory_usage"
    
    # 磁盘使用情况
    local disk_usage=$(df -h /data | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')
    log_info "💾 磁盘使用: $disk_usage"
}

# 备份功能
backup() {
    local backup_dir="/data/backups/$(date +%Y%m%d_%H%M%S)"
    log_info "创建备份到: $backup_dir"
    
    mkdir -p "$backup_dir"
    
    # 备份数据库
    cp -r "$PROJECT_ROOT/data" "$backup_dir/"
    
    # 备份配置文件
    cp "$PROJECT_ROOT/config.yaml" "$backup_dir/"
    
    # 备份知识库
    cp -r "$PROJECT_ROOT/dfy_langchain" "$backup_dir/"
    
    log_info "备份完成: $backup_dir"
}

# 更新功能
update() {
    local deployment_type=$(detect_deployment_type)
    
    log_info "开始更新应用..."
    
    # 创建备份
    backup
    
    case $deployment_type in
        "systemd")
            systemd_stop
            # 这里可以添加代码更新逻辑
            systemd_start
            ;;
        "docker")
            docker_stop
            docker_build
            docker_start
            ;;
        *)
            log_error "未检测到运行中的服务"
            exit 1
            ;;
    esac
    
    # 等待服务启动
    sleep 10
    health_check
}

# 显示帮助信息
show_help() {
    echo "智能体平台管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看服务日志"
    echo "  health      健康检查"
    echo "  backup      备份数据"
    echo "  update      更新应用"
    echo "  build       构建Docker镜像 (仅Docker部署)"
    echo ""
    echo "示例:"
    echo "  $0 status"
    echo "  $0 restart"
    echo "  $0 health"
}

# 主函数
main() {
    local command="$1"
    local deployment_type=$(detect_deployment_type)
    
    if [ -z "$command" ]; then
        show_help
        exit 0
    fi
    
    log_debug "检测到部署类型: $deployment_type"
    
    case $command in
        "start")
            case $deployment_type in
                "systemd") systemd_start ;;
                "docker") docker_start ;;
                "none") 
                    log_error "未检测到已部署的服务"
                    echo "请先运行部署脚本: ./deploy/deploy.sh"
                    exit 1
                    ;;
            esac
            ;;
        "stop")
            case $deployment_type in
                "systemd") systemd_stop ;;
                "docker") docker_stop ;;
                "none") log_warn "没有运行中的服务" ;;
            esac
            ;;
        "restart")
            case $deployment_type in
                "systemd") systemd_restart ;;
                "docker") docker_restart ;;
                "none") log_error "没有运行中的服务需要重启" ;;
            esac
            ;;
        "status")
            case $deployment_type in
                "systemd") systemd_status ;;
                "docker") docker_status ;;
                "none") log_warn "没有运行中的服务" ;;
            esac
            ;;
        "logs")
            case $deployment_type in
                "systemd") systemd_logs ;;
                "docker") docker_logs ;;
                "none") log_warn "没有运行中的服务" ;;
            esac
            ;;
        "health")
            health_check
            ;;
        "backup")
            backup
            ;;
        "update")
            update
            ;;
        "build")
            if [ "$deployment_type" = "docker" ] || [ "$deployment_type" = "none" ]; then
                docker_build
            else
                log_error "build 命令仅适用于 Docker 部署"
            fi
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 检查是否为root用户（某些操作需要）
if [[ $EUID -ne 0 ]] && [[ "$1" =~ ^(start|stop|restart|update)$ ]]; then
    log_error "此操作需要root权限"
    exit 1
fi

# 执行主函数
main "$@" 