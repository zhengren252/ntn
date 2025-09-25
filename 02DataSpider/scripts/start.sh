#!/bin/bash

# 信息源爬虫模组启动脚本
# 支持多环境部署和服务管理

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
信息源爬虫模组启动脚本

用法: $0 [选项] <环境> <操作>

环境:
  dev, development    开发环境
  staging            测试环境
  prod, production   生产环境

操作:
  start              启动服务
  stop               停止服务
  restart            重启服务
  status             查看状态
  logs               查看日志
  health             健康检查
  backup             数据备份
  clean              清理资源

选项:
  -h, --help         显示帮助信息
  -v, --verbose      详细输出
  -f, --force        强制执行
  --no-build         跳过构建步骤
  --pull             拉取最新镜像

示例:
  $0 dev start                    # 启动开发环境
  $0 prod restart --no-build      # 重启生产环境（跳过构建）
  $0 staging logs                 # 查看测试环境日志
  $0 prod backup                  # 备份生产环境数据

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 设置环境变量
setup_environment() {
    local env=$1
    
    log_info "设置 $env 环境变量..."
    
    # 设置环境文件路径
    case $env in
        "dev"|"development")
            export ENV_FILE=".env.dev"
            export COMPOSE_FILE="docker-compose.dev.yml"
            export PROJECT_NAME="info-crawler-dev"
            ;;
        "staging")
            export ENV_FILE=".env.staging"
            export COMPOSE_FILE="docker-compose.staging.yml"
            export PROJECT_NAME="info-crawler-staging"
            ;;
        "prod"|"production")
            export ENV_FILE=".env.prod"
            export COMPOSE_FILE="docker-compose.prod.yml"
            export PROJECT_NAME="info-crawler-prod"
            ;;
        *)
            log_error "不支持的环境: $env"
            exit 1
            ;;
    esac
    
    # 检查环境文件是否存在
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "环境文件不存在: $ENV_FILE"
        exit 1
    fi
    
    # 加载环境变量
    set -a
    source "$ENV_FILE"
    set +a
    
    log_success "环境变量设置完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    local dirs=(
        "data/sqlite"
        "data/redis"
        "data/logs"
        "data/backups"
        "data/uploads"
        "data/cache"
        "config/ssl"
        "scripts/logs"
    )
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done
    
    # 设置权限
    chmod 755 data/
    chmod 644 data/sqlite/ 2>/dev/null || true
    chmod 755 data/logs/
    
    log_success "目录创建完成"
}

# 构建镜像
build_images() {
    if [[ "$NO_BUILD" == "true" ]]; then
        log_info "跳过构建步骤"
        return
    fi
    
    log_info "构建Docker镜像..."
    
    if [[ "$PULL" == "true" ]]; then
        log_info "拉取基础镜像..."
        docker-compose -f "$COMPOSE_FILE" pull
    fi
    
    docker-compose -f "$COMPOSE_FILE" build
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动服务
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_success "服务启动成功"
        show_service_info
    else
        log_error "服务启动失败"
        docker-compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    docker-compose -f "$COMPOSE_FILE" down
    
    log_success "服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    
    stop_services
    sleep 5
    start_services
}

# 查看服务状态
show_status() {
    log_info "服务状态:"
    
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo
    log_info "容器资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 查看日志
show_logs() {
    local service=${1:-}
    
    if [[ -n "$service" ]]; then
        log_info "查看 $service 服务日志:"
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        log_info "查看所有服务日志:"
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 运行健康检查脚本
    if [[ -f "scripts/health_check.py" ]]; then
        python3 scripts/health_check.py --env "$ENV" --format json
    else
        log_warning "健康检查脚本不存在"
    fi
    
    # 检查服务端点
    local endpoints=(
        "http://localhost:${API_PORT:-5000}/health"
        "http://localhost:${FRONTEND_PORT:-3000}/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s "$endpoint" > /dev/null; then
            log_success "$endpoint 可访问"
        else
            log_error "$endpoint 不可访问"
        fi
    done
}

# 数据备份
backup_data() {
    log_info "执行数据备份..."
    
    if [[ -f "scripts/backup.py" ]]; then
        python3 scripts/backup.py --env "$ENV" --type full
    else
        log_error "备份脚本不存在"
        exit 1
    fi
}

# 清理资源
clean_resources() {
    log_info "清理Docker资源..."
    
    if [[ "$FORCE" == "true" ]]; then
        # 强制清理
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
        docker system prune -f
        docker volume prune -f
    else
        # 温和清理
        docker-compose -f "$COMPOSE_FILE" down --remove-orphans
        docker image prune -f
    fi
    
    log_success "资源清理完成"
}

# 显示服务信息
show_service_info() {
    echo
    log_info "服务访问信息:"
    echo "  前端界面: http://localhost:${FRONTEND_PORT:-3000}"
    echo "  API接口:  http://localhost:${API_PORT:-5000}"
    echo "  监控面板: http://localhost:${GRAFANA_PORT:-3001}"
    echo "  Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}"
    echo
}

# 主函数
main() {
    local env=""
    local action=""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            -f|--force)
                FORCE="true"
                shift
                ;;
            --no-build)
                NO_BUILD="true"
                shift
                ;;
            --pull)
                PULL="true"
                shift
                ;;
            dev|development|staging|prod|production)
                env="$1"
                shift
                ;;
            start|stop|restart|status|logs|health|backup|clean)
                action="$1"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查必需参数
    if [[ -z "$env" ]] || [[ -z "$action" ]]; then
        log_error "缺少必需参数"
        show_help
        exit 1
    fi
    
    # 切换到脚本目录
    cd "$(dirname "$0")/.."
    
    # 执行操作
    case $action in
        "start")
            check_dependencies
            setup_environment "$env"
            create_directories
            build_images
            start_services
            ;;
        "stop")
            setup_environment "$env"
            stop_services
            ;;
        "restart")
            check_dependencies
            setup_environment "$env"
            restart_services
            ;;
        "status")
            setup_environment "$env"
            show_status
            ;;
        "logs")
            setup_environment "$env"
            show_logs "$2"
            ;;
        "health")
            setup_environment "$env"
            health_check
            ;;
        "backup")
            setup_environment "$env"
            backup_data
            ;;
        "clean")
            setup_environment "$env"
            clean_resources
            ;;
        *)
            log_error "不支持的操作: $action"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"