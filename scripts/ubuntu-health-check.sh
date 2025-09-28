#!/bin/bash
# Ubuntu虚拟机环境 - NTN系统健康检查脚本
# 适用于Ubuntu 22.04.5 + Docker环境

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

# 检查Docker环境
check_docker_environment() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装或不在PATH中"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! systemctl is-active --quiet docker; then
        log_error "Docker服务未运行"
        exit 1
    fi
    
    # 检查Docker权限
    if ! docker ps &> /dev/null; then
        log_error "Docker权限不足，请确保用户在docker组中"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 检查系统资源
check_system_resources() {
    log_info "检查系统资源..."
    
    # 检查内存
    TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    
    if [ "$TOTAL_MEM" -lt 8192 ]; then
        log_warning "系统内存不足8GB，当前: ${TOTAL_MEM}MB"
    fi
    
    if [ "$AVAILABLE_MEM" -lt 4096 ]; then
        log_warning "可用内存不足4GB，当前: ${AVAILABLE_MEM}MB"
    fi
    
    # 检查磁盘空间
    DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 80 ]; then
        log_warning "磁盘使用率过高: ${DISK_USAGE}%"
    fi
    
    log_success "系统资源检查完成"
}

# 检查端口占用
check_port_conflicts() {
    log_info "检查端口冲突..."
    
    PORTS=(80 443 3000 3001 3002 3003 3004 3005 3006 5000 5001 5002 5003 5004 5005 5006 5007 5008 5009 5010 6379 8000 9090)
    CONFLICTS=0
    
    for port in "${PORTS[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            PROCESS=$(lsof -ti:$port 2>/dev/null || echo "unknown")
            log_warning "端口 $port 已被占用 (PID: $PROCESS)"
            CONFLICTS=$((CONFLICTS + 1))
        fi
    done
    
    if [ $CONFLICTS -eq 0 ]; then
        log_success "无端口冲突"
    else
        log_warning "发现 $CONFLICTS 个端口冲突"
    fi
}

# 启动容器服务
start_containers() {
    log_info "启动NTN容器服务..."
    
    # 检查docker-compose.prod.yml文件
    if [ ! -f "docker-compose.prod.yml" ]; then
        log_error "docker-compose.prod.yml文件不存在"
        exit 1
    fi
    
    # 清理旧容器
    log_info "清理旧容器..."
    docker-compose -f docker-compose.prod.yml down --remove-orphans
    
    # 清理Docker缓存
    log_info "清理Docker缓存..."
    docker system prune -f
    
    # 启动服务
    log_info "构建并启动所有服务..."
    if docker-compose -f docker-compose.prod.yml up --build -d; then
        log_success "容器启动命令执行成功"
    else
        log_error "容器启动失败"
        exit 1
    fi
    
    # 等待容器启动
    log_info "等待容器启动完成..."
    sleep 30
}

# 检查容器状态
check_container_status() {
    log_info "检查容器运行状态..."
    
    # 预期的容器列表
    EXPECTED_CONTAINERS=(
        "redis"
        "01APIForge"
        "02DataSpider"
        "03ScanPulse"
        "04OptiCore"
        "05-07TradeGuard"
        "08NeuroHub"
        "09MMS"
        "10ReviewGuard-backend"
        "10ReviewGuard-frontend"
        "11ASTSConsole"
        "12TACoreService"
        "13AI Strategy Assistant"
        "14Observability Center"
        "nginx"
    )
    
    RUNNING_COUNT=0
    HEALTHY_COUNT=0
    
    echo
    printf "%-35s %-15s %-15s\n" "容器名称" "运行状态" "健康状态"
    printf "%-35s %-15s %-15s\n" "---" "---" "---"
    
    for container in "${EXPECTED_CONTAINERS[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^$container$"; then
            STATUS="运行中"
            RUNNING_COUNT=$((RUNNING_COUNT + 1))
            
            # 检查健康状态
            HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
            case $HEALTH in
                "healthy")
                    HEALTH_STATUS="健康"
                    HEALTHY_COUNT=$((HEALTHY_COUNT + 1))
                    ;;
                "unhealthy")
                    HEALTH_STATUS="不健康"
                    ;;
                "starting")
                    HEALTH_STATUS="启动中"
                    ;;
                *)
                    HEALTH_STATUS="无检查"
                    ;;
            esac
        else
            STATUS="未运行"
            HEALTH_STATUS="N/A"
        fi
        
        printf "%-35s %-15s %-15s\n" "$container" "$STATUS" "$HEALTH_STATUS"
    done
    
    echo
    log_info "容器状态统计: $RUNNING_COUNT/${#EXPECTED_CONTAINERS[@]} 运行中, $HEALTHY_COUNT 健康"
    
    if [ $RUNNING_COUNT -eq ${#EXPECTED_CONTAINERS[@]} ]; then
        log_success "所有容器都在运行"
    else
        log_error "有容器未运行"
    fi
}

# 检查服务健康端点
check_service_endpoints() {
    log_info "检查服务健康端点..."
    
    # 等待服务完全启动
    log_info "等待服务完全启动..."
    sleep 60
    
    # 健康端点列表
    declare -A ENDPOINTS=(
        ["Redis"]="redis-cli -h localhost -p 6379 ping"
        ["API Factory"]="curl -f -s http://localhost:8000/health"
        ["Info Crawler"]="curl -f -s http://localhost:5001/health"
        ["Scanner"]="curl -f -s http://localhost:5002/health"
        ["Strategy Optimizer"]="curl -f -s http://localhost:5003/health"
        ["Trade Guard"]="curl -f -s http://localhost:5004/health"
        ["Neuro Hub"]="curl -f -s http://localhost:5005/health"
        ["MMS"]="curl -f -s http://localhost:5006/health"
        ["Review Guard Backend"]="curl -f -s http://localhost:5007/health"
        ["TACoreService"]="curl -f -s http://localhost:5008/health"
        ["AI Strategy Assistant"]="curl -f -s http://localhost:5009/health"
        ["Observability Center"]="curl -f -s http://localhost:5010/health"
    )
    
    # 前端端点列表
    declare -A FRONTEND_ENDPOINTS=(
        ["ASTS Console"]="curl -f -s -o /dev/null http://localhost:3000"
        ["Strategy Optimizer Frontend"]="curl -f -s -o /dev/null http://localhost:3001"
        ["Trade Guard Frontend"]="curl -f -s -o /dev/null http://localhost:3002"
        ["Neuro Hub Frontend"]="curl -f -s -o /dev/null http://localhost:3003"
        ["Review Guard Frontend"]="curl -f -s -o /dev/null http://localhost:3004"
        ["Observability Dashboard"]="curl -f -s -o /dev/null http://localhost:3005"
        ["Grafana"]="curl -f -s -o /dev/null http://localhost:3006"
    )
    
    HEALTHY_SERVICES=0
    TOTAL_SERVICES=$((${#ENDPOINTS[@]} + ${#FRONTEND_ENDPOINTS[@]}))
    
    echo
    log_info "检查后端服务健康端点..."
    for service in "${!ENDPOINTS[@]}"; do
        if eval "${ENDPOINTS[$service]}" &>/dev/null; then
            log_success "$service: 健康"
            HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
        else
            log_error "$service: 不健康或无响应"
        fi
    done
    
    echo
    log_info "检查前端服务端点..."
    for service in "${!FRONTEND_ENDPOINTS[@]}"; do
        if eval "${FRONTEND_ENDPOINTS[$service]}" &>/dev/null; then
            log_success "$service: 可访问"
            HEALTHY_SERVICES=$((HEALTHY_SERVICES + 1))
        else
            log_error "$service: 不可访问"
        fi
    done
    
    echo
    log_info "服务健康统计: $HEALTHY_SERVICES/$TOTAL_SERVICES 服务正常"
}

# 生成健康检查报告
generate_health_report() {
    log_info "生成健康检查报告..."
    
    REPORT_FILE="health-check-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "======================================"
        echo "NTN系统健康检查报告"
        echo "======================================"
        echo "检查时间: $(date)"
        echo "环境: Ubuntu 22.04.5 虚拟机 + Docker"
        echo
        
        echo "系统信息:"
        echo "- Ubuntu版本: $(lsb_release -d | cut -f2)"
        echo "- Docker版本: $(docker --version)"
        echo "- Docker Compose版本: $(docker-compose --version)"
        echo "- 系统内存: $(free -h | awk 'NR==2{printf "%s/%s", $3,$2}')"
        echo "- 磁盘使用: $(df -h . | awk 'NR==2 {print $5}')"
        echo
        
        echo "容器状态:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        
        echo "健康检查状态:"
        docker ps --filter "health=healthy" --format "table {{.Names}}\t{{.Status}}"
        echo
        
        echo "异常容器:"
        docker ps --filter "health=unhealthy" --format "table {{.Names}}\t{{.Status}}"
        echo
        
        echo "资源使用:"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        
    } > "$REPORT_FILE"
    
    log_success "健康检查报告已生成: $REPORT_FILE"
}

# 主函数
main() {
    echo "======================================"
    echo "NTN系统健康检查 - Ubuntu虚拟机版本"
    echo "======================================"
    echo "开始时间: $(date)"
    echo
    
    check_docker_environment
    check_system_resources
    check_port_conflicts
    
    # 询问是否启动容器
    read -p "是否启动NTN容器服务? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_containers
    fi
    
    check_container_status
    check_service_endpoints
    generate_health_report
    
    echo
    log_success "健康检查完成!"
    echo "======================================"
}

# 执行主函数
main "$@"