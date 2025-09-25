#!/bin/bash
# 扫描器模组Docker部署脚本
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
扫描器模组Docker部署脚本

用法: $0 [选项] <命令> [环境]

命令:
  start     启动服务
  stop      停止服务
  restart   重启服务
  build     构建镜像
  logs      查看日志
  status    查看状态
  clean     清理资源
  health    健康检查

环境:
  dev       开发环境 (默认)
  prod      生产环境

选项:
  -h, --help     显示帮助信息
  -v, --verbose  详细输出
  -f, --force    强制执行
  --no-cache     构建时不使用缓存
  --pull         构建前拉取最新基础镜像

示例:
  $0 start dev              # 启动开发环境
  $0 build prod --no-cache  # 无缓存构建生产环境
  $0 logs dev               # 查看开发环境日志
  $0 health prod            # 生产环境健康检查
EOF
}

# 解析参数
VERBOSE=false
FORCE=false
NO_CACHE=false
PULL=false
ENVIRONMENT="dev"
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --pull)
            PULL=true
            shift
            ;;
        start|stop|restart|build|logs|status|clean|health)
            COMMAND=$1
            shift
            ;;
        dev|prod)
            ENVIRONMENT=$1
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查命令
if [[ -z "$COMMAND" ]]; then
    log_error "请指定命令"
    show_help
    exit 1
fi

# 设置环境变量
if [[ "$ENVIRONMENT" == "dev" ]]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    PROJECT_NAME="scanner-dev"
else
    COMPOSE_FILE="docker-compose.yml"
    PROJECT_NAME="scanner-prod"
fi

# 详细输出设置
if [[ "$VERBOSE" == "true" ]]; then
    set -x
fi

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装或不在PATH中"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 构建镜像
build_images() {
    log_info "构建${ENVIRONMENT}环境镜像..."
    
    BUILD_ARGS=""
    if [[ "$NO_CACHE" == "true" ]]; then
        BUILD_ARGS="$BUILD_ARGS --no-cache"
    fi
    if [[ "$PULL" == "true" ]]; then
        BUILD_ARGS="$BUILD_ARGS --pull"
    fi
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build $BUILD_ARGS
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动${ENVIRONMENT}环境服务..."
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    
    log_success "服务启动完成"
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10
    
    # 显示服务状态
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
}

# 停止服务
stop_services() {
    log_info "停止${ENVIRONMENT}环境服务..."
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启${ENVIRONMENT}环境服务..."
    
    stop_services
    start_services
    
    log_success "服务重启完成"
}

# 查看日志
show_logs() {
    log_info "显示${ENVIRONMENT}环境日志..."
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
}

# 查看状态
show_status() {
    log_info "${ENVIRONMENT}环境服务状态:"
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    
    echo
    log_info "容器资源使用情况:"
    docker stats --no-stream $(docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps -q)
}

# 清理资源
clean_resources() {
    log_warning "清理${ENVIRONMENT}环境资源..."
    
    if [[ "$FORCE" != "true" ]]; then
        read -p "确定要清理所有资源吗？这将删除容器、网络和卷 [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "取消清理操作"
            exit 0
        fi
    fi
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v --remove-orphans
    docker system prune -f
    
    log_success "资源清理完成"
}

# 健康检查
health_check() {
    log_info "执行${ENVIRONMENT}环境健康检查..."
    
    # 检查容器状态
    CONTAINERS=$(docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps -q)
    
    if [[ -z "$CONTAINERS" ]]; then
        log_error "没有运行的容器"
        exit 1
    fi
    
    ALL_HEALTHY=true
    
    for container in $CONTAINERS; do
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
        NAME=$(docker inspect --format='{{.Name}}' "$container" | sed 's/^\///')
        
        if [[ "$HEALTH" == "healthy" ]] || [[ "$HEALTH" == "no-health-check" ]]; then
            log_success "$NAME: 健康"
        else
            log_error "$NAME: 不健康 ($HEALTH)"
            ALL_HEALTHY=false
        fi
    done
    
    if [[ "$ALL_HEALTHY" == "true" ]]; then
        log_success "所有服务健康"
        exit 0
    else
        log_error "部分服务不健康"
        exit 1
    fi
}

# 主逻辑
main() {
    check_dependencies
    
    case $COMMAND in
        build)
            build_images
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        clean)
            clean_resources
            ;;
        health)
            health_check
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main