#!/bin/bash

# 交易执行铁三角项目服务启动脚本
# 用途：启动所有必要的服务和组件

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_NAME="tradeguard"
DEFAULT_ENV="development"
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=2

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

# 检查端口是否被占用
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -i :$port &> /dev/null; then
        log_warning "端口 $port 已被占用 ($service_name)"
        return 1
    fi
    return 0
}

# 等待服务启动
wait_for_service() {
    local url=$1
    local service_name=$2
    local timeout=${3:-$HEALTH_CHECK_TIMEOUT}
    
    log_info "等待 $service_name 服务启动..."
    
    local count=0
    local max_attempts=$((timeout / HEALTH_CHECK_INTERVAL))
    
    while [ $count -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log_success "$service_name 服务已启动"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        count=$((count + 1))
        echo -n "."
    done
    
    echo ""
    log_error "$service_name 服务启动超时"
    return 1
}

# 启动Redis服务
start_redis() {
    log_info "启动Redis服务..."
    
    if docker ps | grep -q "${PROJECT_NAME}_redis"; then
        log_info "Redis服务已在运行"
        return 0
    fi
    
    # 停止可能存在的旧容器
    docker stop "${PROJECT_NAME}_redis" 2>/dev/null || true
    docker rm "${PROJECT_NAME}_redis" 2>/dev/null || true
    
    # 启动Redis容器
    docker run -d \
        --name "${PROJECT_NAME}_redis" \
        --restart unless-stopped \
        -p 6379:6379 \
        -v "${PROJECT_NAME}_redis_data:/data" \
        redis:7-alpine redis-server --appendonly yes
    
    # 等待Redis启动
    sleep 3
    
    if docker ps | grep -q "${PROJECT_NAME}_redis"; then
        log_success "Redis服务启动成功"
    else
        log_error "Redis服务启动失败"
        return 1
    fi
}

# 启动ZeroMQ代理
start_zeromq_broker() {
    log_info "启动ZeroMQ消息代理..."
    
    # 检查是否已有ZeroMQ代理在运行
    if pgrep -f "zmq.*broker" > /dev/null; then
        log_info "ZeroMQ代理已在运行"
        return 0
    fi
    
    # 启动ZeroMQ代理 (使用Node.js脚本)
    nohup node scripts/zmq-broker.js > logs/zmq-broker.log 2>&1 &
    local broker_pid=$!
    
    # 保存PID
    echo $broker_pid > temp/zmq-broker.pid
    
    sleep 2
    
    if kill -0 $broker_pid 2>/dev/null; then
        log_success "ZeroMQ代理启动成功 (PID: $broker_pid)"
    else
        log_error "ZeroMQ代理启动失败"
        return 1
    fi
}

# 启动后端API服务
start_backend() {
    local env=${1:-$DEFAULT_ENV}
    
    log_info "启动后端API服务 (环境: $env)..."
    
    # 检查端口
    if ! check_port 3001 "Backend API"; then
        log_error "后端API端口被占用，请检查是否有其他实例在运行"
        return 1
    fi
    
    # 设置环境变量
    export NODE_ENV=$env
    
    # 启动后端服务
    if [ "$env" = "development" ]; then
        nohup npm run dev:api > logs/backend.log 2>&1 &
    else
        nohup npm run start:api > logs/backend.log 2>&1 &
    fi
    
    local backend_pid=$!
    echo $backend_pid > temp/backend.pid
    
    # 等待后端服务启动
    if wait_for_service "http://localhost:3001/health" "Backend API"; then
        log_success "后端API服务启动成功 (PID: $backend_pid)"
    else
        log_error "后端API服务启动失败"
        return 1
    fi
}

# 启动前端开发服务器
start_frontend() {
    local env=${1:-$DEFAULT_ENV}
    
    if [ "$env" != "development" ]; then
        log_info "生产环境不需要启动前端开发服务器"
        return 0
    fi
    
    log_info "启动前端开发服务器..."
    
    # 检查端口
    if ! check_port 5173 "Frontend Dev Server"; then
        log_error "前端开发服务器端口被占用，请检查是否有其他实例在运行"
        return 1
    fi
    
    # 启动前端开发服务器
    nohup npm run dev > logs/frontend.log 2>&1 &
    local frontend_pid=$!
    echo $frontend_pid > temp/frontend.pid
    
    # 等待前端服务启动
    if wait_for_service "http://localhost:5173" "Frontend Dev Server"; then
        log_success "前端开发服务器启动成功 (PID: $frontend_pid)"
    else
        log_error "前端开发服务器启动失败"
        return 1
    fi
}

# 启动交易员模组
start_trader_module() {
    log_info "启动交易员模组..."
    
    nohup node api/modules/trader/index.js > logs/trader-module.log 2>&1 &
    local trader_pid=$!
    echo $trader_pid > temp/trader-module.pid
    
    sleep 2
    
    if kill -0 $trader_pid 2>/dev/null; then
        log_success "交易员模组启动成功 (PID: $trader_pid)"
    else
        log_error "交易员模组启动失败"
        return 1
    fi
}

# 启动风控模组
start_risk_module() {
    log_info "启动风控模组..."
    
    nohup node api/modules/risk/index.js > logs/risk-module.log 2>&1 &
    local risk_pid=$!
    echo $risk_pid > temp/risk-module.pid
    
    sleep 2
    
    if kill -0 $risk_pid 2>/dev/null; then
        log_success "风控模组启动成功 (PID: $risk_pid)"
    else
        log_error "风控模组启动失败"
        return 1
    fi
}

# 启动财务模组
start_finance_module() {
    log_info "启动财务模组..."
    
    nohup node api/modules/finance/index.js > logs/finance-module.log 2>&1 &
    local finance_pid=$!
    echo $finance_pid > temp/finance-module.pid
    
    sleep 2
    
    if kill -0 $finance_pid 2>/dev/null; then
        log_success "财务模组启动成功 (PID: $finance_pid)"
    else
        log_error "财务模组启动失败"
        return 1
    fi
}

# 检查服务健康状态
check_health() {
    log_info "检查服务健康状态..."
    
    local all_healthy=true
    
    # 检查Redis
    if docker ps | grep -q "${PROJECT_NAME}_redis"; then
        log_success "✓ Redis服务正常"
    else
        log_error "✗ Redis服务异常"
        all_healthy=false
    fi
    
    # 检查后端API
    if curl -s "http://localhost:3001/health" > /dev/null 2>&1; then
        log_success "✓ 后端API服务正常"
    else
        log_error "✗ 后端API服务异常"
        all_healthy=false
    fi
    
    # 检查前端 (仅开发环境)
    if [ -f "temp/frontend.pid" ]; then
        if curl -s "http://localhost:5173" > /dev/null 2>&1; then
            log_success "✓ 前端开发服务器正常"
        else
            log_error "✗ 前端开发服务器异常"
            all_healthy=false
        fi
    fi
    
    # 检查模组
    local modules=("trader" "risk" "finance")
    for module in "${modules[@]}"; do
        if [ -f "temp/${module}-module.pid" ] && kill -0 "$(cat temp/${module}-module.pid)" 2>/dev/null; then
            log_success "✓ ${module}模组正常"
        else
            log_error "✗ ${module}模组异常"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        log_success "所有服务运行正常"
        return 0
    else
        log_error "部分服务存在异常"
        return 1
    fi
}

# 停止所有服务
stop_services() {
    log_info "停止所有服务..."
    
    # 停止模组
    local modules=("trader" "risk" "finance" "backend" "frontend" "zmq-broker")
    for module in "${modules[@]}"; do
        local pid_file="temp/${module}.pid"
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                log_info "停止 ${module} (PID: $pid)"
                kill "$pid"
                sleep 1
                # 强制杀死
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done
    
    # 停止Redis容器
    if docker ps | grep -q "${PROJECT_NAME}_redis"; then
        log_info "停止Redis容器"
        docker stop "${PROJECT_NAME}_redis"
    fi
    
    log_success "所有服务已停止"
}

# 重启所有服务
restart_services() {
    local env=${1:-$DEFAULT_ENV}
    
    log_info "重启所有服务..."
    stop_services
    sleep 3
    start_all_services "$env"
}

# 启动所有服务
start_all_services() {
    local env=${1:-$DEFAULT_ENV}
    
    log_info "启动交易执行铁三角项目所有服务 (环境: $env)"
    log_info "================================================"
    
    # 创建必要的目录
    mkdir -p logs temp
    
    # 启动基础服务
    start_redis || return 1
    start_zeromq_broker || return 1
    
    # 启动核心模组
    start_trader_module || return 1
    start_risk_module || return 1
    start_finance_module || return 1
    
    # 启动API和前端
    start_backend "$env" || return 1
    start_frontend "$env" || return 1
    
    log_success "================================================"
    log_success "所有服务启动完成！"
    
    # 显示服务信息
    echo ""
    log_info "服务访问地址:"
    log_info "- 前端应用: http://localhost:5173"
    log_info "- 后端API: http://localhost:3001"
    log_info "- API文档: http://localhost:3001/docs"
    log_info "- 健康检查: http://localhost:3001/health"
    
    echo ""
    log_info "日志文件位置:"
    log_info "- 后端日志: logs/backend.log"
    log_info "- 前端日志: logs/frontend.log"
    log_info "- 交易员模组: logs/trader-module.log"
    log_info "- 风控模组: logs/risk-module.log"
    log_info "- 财务模组: logs/finance-module.log"
    log_info "- ZeroMQ代理: logs/zmq-broker.log"
    
    echo ""
    log_info "使用 '$0 health' 检查服务状态"
    log_info "使用 '$0 stop' 停止所有服务"
}

# 显示帮助信息
show_help() {
    echo "交易执行铁三角项目服务管理脚本"
    echo ""
    echo "用法: $0 <命令> [环境]"
    echo ""
    echo "命令:"
    echo "  start [env]     启动所有服务"
    echo "  stop            停止所有服务"
    echo "  restart [env]   重启所有服务"
    echo "  health          检查服务健康状态"
    echo "  redis           仅启动Redis服务"
    echo "  backend [env]   仅启动后端服务"
    echo "  frontend        仅启动前端服务"
    echo ""
    echo "环境选项:"
    echo "  development  - 开发环境 (默认)"
    echo "  staging      - 预发布环境"
    echo "  production   - 生产环境"
    echo ""
    echo "示例:"
    echo "  $0 start                    # 启动开发环境所有服务"
    echo "  $0 start production         # 启动生产环境所有服务"
    echo "  $0 stop                     # 停止所有服务"
    echo "  $0 restart staging          # 重启预发布环境服务"
    echo "  $0 health                   # 检查服务健康状态"
}

# 主函数
main() {
    local command=${1:-start}
    local env=${2:-$DEFAULT_ENV}
    
    case "$command" in
        start)
            start_all_services "$env"
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services "$env"
            ;;
        health)
            check_health
            ;;
        redis)
            start_redis
            ;;
        backend)
            start_backend "$env"
            ;;
        frontend)
            start_frontend "$env"
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "无效的命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"