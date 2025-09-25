#!/bin/bash
# Ubuntu虚拟机Docker部署脚本
# NeuroTrade Nexus (NTN) 系统部署
# 版本: 1.0.0

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
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

# 系统信息
SYSTEM_NAME="NeuroTrade Nexus (NTN)"
VERSION="1.0.0"
DEPLOY_DIR="/home/tjsga/ntn-deploy"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_DIR="/home/tjsga/ntn-logs"
BACKUP_DIR="/home/tjsga/ntn-backup"

# 容器列表（按照文件夹名称）
EXPECTED_CONTAINERS=(
    "ntn-redis-prod"
    "01APIForge"
    "02DataSpider"
    "03ScanPulse"
    "04OptiCore"
    "05-07TradeGuard"
    "08NeuroHub"
    "09MMS"
    "10ReviewGuard-backend"
    "10ReviewGuard-frontend"
    "11ASTS-Console"
    "12TACoreService"
    "13AI-Strategy-Assistant"
    "14Observability-Center"
    "nginx"
)

# 显示横幅
show_banner() {
    echo -e "${CYAN}"
    echo "=========================================="
    echo "    $SYSTEM_NAME 部署脚本"
    echo "    版本: $VERSION"
    echo "    环境: Ubuntu 22.04.5 LTS"
    echo "    时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo -e "${NC}"
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测操作系统版本"
        exit 1
    fi
    
    source /etc/os-release
    log_info "操作系统: $PRETTY_NAME"
    
    # 检查内存
    TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [[ $TOTAL_MEM -lt 8192 ]]; then
        log_warning "系统内存不足8GB，当前: ${TOTAL_MEM}MB"
    else
        log_success "系统内存充足: ${TOTAL_MEM}MB"
    fi
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $AVAILABLE_SPACE -lt 50 ]]; then
        log_warning "磁盘空间不足50GB，当前可用: ${AVAILABLE_SPACE}GB"
    else
        log_success "磁盘空间充足: ${AVAILABLE_SPACE}GB"
    fi
}

# 检查Docker环境
check_docker_environment() {
    log_info "检查Docker环境..."
    
    # 检查Docker是否安装
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! systemctl is-active --quiet docker; then
        log_warning "Docker服务未运行，正在启动..."
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi
    
    # 显示版本信息
    DOCKER_VERSION=$(docker --version)
    COMPOSE_VERSION=$(docker-compose --version 2>/dev/null || docker compose version)
    
    log_success "Docker环境检查完成"
    log_info "$DOCKER_VERSION"
    log_info "$COMPOSE_VERSION"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p "$DEPLOY_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"
    
    log_success "目录创建完成"
}

# 检查端口占用
check_port_conflicts() {
    log_info "检查端口占用情况..."
    
    PORTS=(80 443 3000 5000 6379 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011 8012 8013 8014 9090 3001)
    CONFLICTS=()
    
    for port in "${PORTS[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            CONFLICTS+=("$port")
            log_warning "端口 $port 已被占用"
        fi
    done
    
    if [[ ${#CONFLICTS[@]} -gt 0 ]]; then
        log_warning "发现端口冲突: ${CONFLICTS[*]}"
        read -p "是否继续部署？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
    else
        log_success "端口检查通过"
    fi
}

# 备份现有部署
backup_existing_deployment() {
    if [[ -f "$DEPLOY_DIR/$COMPOSE_FILE" ]]; then
        log_info "备份现有部署..."
        
        BACKUP_NAME="ntn-backup-$(date +%Y%m%d-%H%M%S)"
        BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
        
        mkdir -p "$BACKUP_PATH"
        
        # 备份配置文件
        cp "$DEPLOY_DIR/$COMPOSE_FILE" "$BACKUP_PATH/"
        
        # 导出容器状态
        cd "$DEPLOY_DIR"
        docker-compose -f "$COMPOSE_FILE" ps > "$BACKUP_PATH/containers-status.txt" 2>/dev/null || true
        
        log_success "备份完成: $BACKUP_PATH"
    fi
}

# 停止现有容器
stop_existing_containers() {
    if [[ -f "$DEPLOY_DIR/$COMPOSE_FILE" ]]; then
        log_info "停止现有容器..."
        
        cd "$DEPLOY_DIR"
        
        # 优雅停止
        docker-compose -f "$COMPOSE_FILE" down --timeout 30 || true
        
        # 清理悬空镜像
        docker image prune -f || true
        
        log_success "现有容器已停止"
    fi
}

# 部署系统
deploy_system() {
    log_info "开始部署 $SYSTEM_NAME..."
    
    cd "$DEPLOY_DIR"
    
    # 检查compose文件
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "找不到 $COMPOSE_FILE 文件"
        exit 1
    fi
    
    # 验证compose文件
    log_info "验证Docker Compose配置..."
    if ! docker-compose -f "$COMPOSE_FILE" config > /dev/null; then
        log_error "Docker Compose配置文件有误"
        exit 1
    fi
    
    # 拉取镜像
    log_info "拉取Docker镜像..."
    docker-compose -f "$COMPOSE_FILE" pull || true
    
    # 构建并启动容器
    log_info "构建并启动容器..."
    docker-compose -f "$COMPOSE_FILE" up --build -d
    
    log_success "系统部署完成"
}

# 等待容器启动
wait_for_containers() {
    log_info "等待容器启动..."
    
    local max_wait=300  # 最大等待5分钟
    local wait_time=0
    local check_interval=10
    
    while [[ $wait_time -lt $max_wait ]]; do
        local running_count=0
        
        for container in "${EXPECTED_CONTAINERS[@]}"; do
            if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
                ((running_count++))
            fi
        done
        
        log_info "容器启动进度: $running_count/${#EXPECTED_CONTAINERS[@]}"
        
        if [[ $running_count -eq ${#EXPECTED_CONTAINERS[@]} ]]; then
            log_success "所有容器已启动"
            return 0
        fi
        
        sleep $check_interval
        ((wait_time += check_interval))
    done
    
    log_warning "容器启动超时，继续进行健康检查"
}

# 检查容器健康状态
check_container_health() {
    log_info "检查容器健康状态..."
    
    cd "$DEPLOY_DIR"
    
    # 显示容器状态
    echo -e "\n${BLUE}=== 容器状态 ===${NC}"
    docker-compose -f "$COMPOSE_FILE" ps
    
    # 检查每个容器
    local healthy_count=0
    local total_count=${#EXPECTED_CONTAINERS[@]}
    
    echo -e "\n${BLUE}=== 详细健康检查 ===${NC}"
    
    for container in "${EXPECTED_CONTAINERS[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep "^$container" | grep -q "Up"; then
            # 检查健康状态
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
            
            if [[ "$health_status" == "healthy" ]] || [[ "$health_status" == "no-healthcheck" ]]; then
                echo -e "${GREEN}✓${NC} $container: 运行正常"
                ((healthy_count++))
            else
                echo -e "${YELLOW}⚠${NC} $container: 健康检查失败 ($health_status)"
            fi
        else
            echo -e "${RED}✗${NC} $container: 未运行"
        fi
    done
    
    echo -e "\n${BLUE}健康容器: $healthy_count/$total_count${NC}"
    
    if [[ $healthy_count -eq $total_count ]]; then
        log_success "所有容器健康检查通过"
        return 0
    else
        log_warning "部分容器健康检查失败"
        return 1
    fi
}

# 验证服务端点
verify_service_endpoints() {
    log_info "验证服务端点..."
    
    # 等待服务启动
    sleep 30
    
    # 定义服务端点
    declare -A ENDPOINTS=(
        ["API Factory"]="http://localhost:8000/health"
        ["Info Crawler"]="http://localhost:8001/health"
        ["Scanner"]="http://localhost:8002/health"
        ["Strategy Optimizer"]="http://localhost:8003/health"
        ["Trade Guard"]="http://localhost:8004/health"
        ["Neuro Hub"]="http://localhost:8005/health"
        ["MMS"]="http://localhost:8006/health"
        ["Review Guard Backend"]="http://localhost:8007/health"
        ["ASTS Console"]="http://localhost:8008/health"
        ["TACore Service"]="http://localhost:8009/health"
        ["AI Strategy Assistant"]="http://localhost:8010/health"
        ["Observability Center"]="http://localhost:8011/health"
        ["Review Guard Frontend"]="http://localhost:3000"
        ["Nginx"]="http://localhost:80"
    )
    
    local success_count=0
    local total_count=${#ENDPOINTS[@]}
    
    echo -e "\n${BLUE}=== 服务端点验证 ===${NC}"
    
    for service in "${!ENDPOINTS[@]}"; do
        local endpoint="${ENDPOINTS[$service]}"
        
        if curl -s --max-time 10 "$endpoint" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} $service: $endpoint"
            ((success_count++))
        else
            echo -e "${RED}✗${NC} $service: $endpoint (无响应)"
        fi
    done
    
    echo -e "\n${BLUE}可用服务: $success_count/$total_count${NC}"
    
    if [[ $success_count -gt $((total_count * 70 / 100)) ]]; then
        log_success "大部分服务端点验证通过"
        return 0
    else
        log_warning "多数服务端点验证失败"
        return 1
    fi
}

# 生成部署报告
generate_deployment_report() {
    local report_file="$LOG_DIR/deployment-report-$(date +%Y%m%d-%H%M%S).txt"
    
    log_info "生成部署报告..."
    
    {
        echo "========================================"
        echo "$SYSTEM_NAME 部署报告"
        echo "========================================"
        echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "部署环境: Ubuntu $(lsb_release -rs)"
        echo "Docker版本: $(docker --version)"
        echo "Compose版本: $(docker-compose --version 2>/dev/null || docker compose version)"
        echo ""
        echo "=== 系统资源 ==="
        echo "内存使用: $(free -h | awk 'NR==2{printf "%.1f/%.1fGB (%.1f%%)", $3/1024/1024, $2/1024/1024, $3*100/$2}')"
        echo "磁盘使用: $(df -h . | awk 'NR==2{print $3"/"$2" ("$5")"}')"
        echo "CPU负载: $(uptime | awk -F'load average:' '{print $2}')"
        echo ""
        echo "=== 容器状态 ==="
        cd "$DEPLOY_DIR"
        docker-compose -f "$COMPOSE_FILE" ps
        echo ""
        echo "=== Docker镜像 ==="
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
        echo ""
        echo "=== 网络配置 ==="
        docker network ls
        echo ""
        echo "=== 卷配置 ==="
        docker volume ls
    } > "$report_file"
    
    log_success "部署报告已生成: $report_file"
}

# 显示部署摘要
show_deployment_summary() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}    部署完成摘要${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}✓ 系统名称:${NC} $SYSTEM_NAME"
    echo -e "${GREEN}✓ 部署时间:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${GREEN}✓ 容器数量:${NC} ${#EXPECTED_CONTAINERS[@]}"
    echo -e "${GREEN}✓ 部署目录:${NC} $DEPLOY_DIR"
    echo -e "${GREEN}✓ 日志目录:${NC} $LOG_DIR"
    echo ""
    echo -e "${BLUE}主要服务端点:${NC}"
    echo -e "  • 前端界面: http://localhost:3000"
    echo -e "  • API网关: http://localhost:80"
    echo -e "  • 监控中心: http://localhost:8011"
    echo ""
    echo -e "${YELLOW}管理命令:${NC}"
    echo -e "  • 查看状态: docker-compose -f $COMPOSE_FILE ps"
    echo -e "  • 查看日志: docker-compose -f $COMPOSE_FILE logs -f [服务名]"
    echo -e "  • 停止系统: docker-compose -f $COMPOSE_FILE down"
    echo -e "  • 重启系统: docker-compose -f $COMPOSE_FILE restart"
    echo -e "${CYAN}========================================${NC}"
}

# 主函数
main() {
    show_banner
    
    # 检查是否以root权限运行
    if [[ $EUID -eq 0 ]]; then
        log_warning "建议不要以root权限运行此脚本"
    fi
    
    # 执行部署步骤
    check_system_requirements
    check_docker_environment
    create_directories
    check_port_conflicts
    backup_existing_deployment
    stop_existing_containers
    deploy_system
    wait_for_containers
    
    # 健康检查
    local health_ok=true
    if ! check_container_health; then
        health_ok=false
    fi
    
    if ! verify_service_endpoints; then
        health_ok=false
    fi
    
    # 生成报告
    generate_deployment_report
    
    # 显示摘要
    show_deployment_summary
    
    if [[ "$health_ok" == "true" ]]; then
        log_success "$SYSTEM_NAME 部署成功！"
        exit 0
    else
        log_warning "$SYSTEM_NAME 部署完成，但存在一些问题，请检查日志"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi