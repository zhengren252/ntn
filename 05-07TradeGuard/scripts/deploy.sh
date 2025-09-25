#!/bin/bash

# 交易执行铁三角项目Docker部署脚本
# 用途：自动化容器部署和管理

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
REGISTRY="localhost:5000"  # 本地镜像仓库
VERSION=$(date +"%Y%m%d_%H%M%S")
DOCKER_COMPOSE_FILE="docker-compose.yml"

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
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 构建镜像
build_images() {
    local env=${1:-$DEFAULT_ENV}
    
    log_info "构建Docker镜像 (环境: $env)..."
    
    # 构建基础镜像
    log_info "构建基础镜像..."
    docker build -t "${PROJECT_NAME}:base" -f docker/Dockerfile.base .
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker build -t "${PROJECT_NAME}:frontend-${env}" \
        --build-arg NODE_ENV="$env" \
        -f docker/Dockerfile.frontend .
    
    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t "${PROJECT_NAME}:backend-${env}" \
        --build-arg NODE_ENV="$env" \
        -f docker/Dockerfile.backend .
    
    # 构建交易员模组镜像
    log_info "构建交易员模组镜像..."
    docker build -t "${PROJECT_NAME}:trader-${env}" \
        --build-arg NODE_ENV="$env" \
        -f docker/Dockerfile.trader .
    
    # 构建风控模组镜像
    log_info "构建风控模组镜像..."
    docker build -t "${PROJECT_NAME}:risk-${env}" \
        --build-arg NODE_ENV="$env" \
        -f docker/Dockerfile.risk .
    
    # 构建财务模组镜像
    log_info "构建财务模组镜像..."
    docker build -t "${PROJECT_NAME}:finance-${env}" \
        --build-arg NODE_ENV="$env" \
        -f docker/Dockerfile.finance .
    
    log_success "所有镜像构建完成"
}

# 推送镜像到仓库
push_images() {
    local env=${1:-$DEFAULT_ENV}
    
    log_info "推送镜像到仓库..."
    
    local images=(
        "${PROJECT_NAME}:base"
        "${PROJECT_NAME}:frontend-${env}"
        "${PROJECT_NAME}:backend-${env}"
        "${PROJECT_NAME}:trader-${env}"
        "${PROJECT_NAME}:risk-${env}"
        "${PROJECT_NAME}:finance-${env}"
    )
    
    for image in "${images[@]}"; do
        local registry_image="${REGISTRY}/${image}"
        
        log_info "推送镜像: $image -> $registry_image"
        docker tag "$image" "$registry_image"
        docker push "$registry_image"
    done
    
    log_success "所有镜像推送完成"
}

# 生成Docker Compose文件
generate_compose_file() {
    local env=${1:-$DEFAULT_ENV}
    
    log_info "生成Docker Compose文件 (环境: $env)..."
    
    cat > "$DOCKER_COMPOSE_FILE" << EOF
version: '3.8'

services:
  # Redis缓存服务
  redis:
    image: redis:7-alpine
    container_name: ${PROJECT_NAME}_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    networks:
      - tradeguard_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ZeroMQ消息代理
  zmq-broker:
    image: ${PROJECT_NAME}:backend-${env}
    container_name: ${PROJECT_NAME}_zmq_broker
    restart: unless-stopped
    ports:
      - "5555:5555"
      - "5556:5556"
      - "5557:5557"
      - "5558:5558"
    environment:
      - NODE_ENV=${env}
      - LOG_LEVEL=info
    command: node scripts/zmq-broker.js
    networks:
      - tradeguard_network
    healthcheck:
      test: ["CMD", "node", "-e", "require('net').createConnection(5555, 'localhost').on('connect', () => process.exit(0)).on('error', () => process.exit(1))"]
      interval: 10s
      timeout: 5s
      retries: 3

  # 后端API服务
  backend:
    image: ${PROJECT_NAME}:backend-${env}
    container_name: ${PROJECT_NAME}_backend
    restart: unless-stopped
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=${env}
      - REDIS_URL=redis://redis:6379
      - ZMQ_FRONTEND_URL=tcp://zmq-broker:5555
      - ZMQ_BACKEND_URL=tcp://zmq-broker:5556
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      redis:
        condition: service_healthy
      zmq-broker:
        condition: service_healthy
    networks:
      - tradeguard_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3001/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # 交易员模组
  trader:
    image: ${PROJECT_NAME}:trader-${env}
    container_name: ${PROJECT_NAME}_trader
    restart: unless-stopped
    environment:
      - NODE_ENV=${env}
      - REDIS_URL=redis://redis:6379
      - ZMQ_FRONTEND_URL=tcp://zmq-broker:5555
      - ZMQ_BACKEND_URL=tcp://zmq-broker:5556
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      redis:
        condition: service_healthy
      zmq-broker:
        condition: service_healthy
    networks:
      - tradeguard_network

  # 风控模组
  risk:
    image: ${PROJECT_NAME}:risk-${env}
    container_name: ${PROJECT_NAME}_risk
    restart: unless-stopped
    environment:
      - NODE_ENV=${env}
      - REDIS_URL=redis://redis:6379
      - ZMQ_FRONTEND_URL=tcp://zmq-broker:5555
      - ZMQ_BACKEND_URL=tcp://zmq-broker:5556
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      redis:
        condition: service_healthy
      zmq-broker:
        condition: service_healthy
    networks:
      - tradeguard_network

  # 财务模组
  finance:
    image: ${PROJECT_NAME}:finance-${env}
    container_name: ${PROJECT_NAME}_finance
    restart: unless-stopped
    environment:
      - NODE_ENV=${env}
      - REDIS_URL=redis://redis:6379
      - ZMQ_FRONTEND_URL=tcp://zmq-broker:5555
      - ZMQ_BACKEND_URL=tcp://zmq-broker:5556
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      redis:
        condition: service_healthy
      zmq-broker:
        condition: service_healthy
    networks:
      - tradeguard_network
EOF

    # 如果是开发环境，添加前端服务
    if [ "$env" = "development" ]; then
        cat >> "$DOCKER_COMPOSE_FILE" << EOF

  # 前端开发服务器 (仅开发环境)
  frontend:
    image: ${PROJECT_NAME}:frontend-${env}
    container_name: ${PROJECT_NAME}_frontend
    restart: unless-stopped
    ports:
      - "5173:5173"
    environment:
      - NODE_ENV=${env}
      - VITE_API_URL=http://localhost:3001
    volumes:
      - ./src:/app/src
      - ./public:/app/public
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - tradeguard_network
EOF
    fi

    # 添加网络和卷定义
    cat >> "$DOCKER_COMPOSE_FILE" << EOF

networks:
  tradeguard_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  redis_data:
    driver: local
EOF

    log_success "Docker Compose文件生成完成: $DOCKER_COMPOSE_FILE"
}

# 部署服务
deploy() {
    local env=${1:-$DEFAULT_ENV}
    local action=${2:-up}
    
    log_info "部署服务 (环境: $env, 操作: $action)..."
    
    # 生成Compose文件
    generate_compose_file "$env"
    
    case "$action" in
        up)
            # 启动服务
            docker-compose up -d
            
            # 等待服务启动
            log_info "等待服务启动..."
            sleep 10
            
            # 检查服务状态
            check_services_health
            ;;
        down)
            # 停止服务
            docker-compose down
            ;;
        restart)
            # 重启服务
            docker-compose restart
            ;;
        logs)
            # 查看日志
            docker-compose logs -f
            ;;
        *)
            log_error "无效的部署操作: $action"
            exit 1
            ;;
    esac
    
    log_success "部署操作完成: $action"
}

# 检查服务健康状态
check_services_health() {
    log_info "检查服务健康状态..."
    
    local services=("redis" "zmq-broker" "backend" "trader" "risk" "finance")
    local all_healthy=true
    
    for service in "${services[@]}"; do
        local container_name="${PROJECT_NAME}_${service//-/_}"
        
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
            # 检查健康状态
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
            
            case "$health" in
                "healthy")
                    log_success "✓ $service 服务健康"
                    ;;
                "unhealthy")
                    log_error "✗ $service 服务不健康"
                    all_healthy=false
                    ;;
                "starting")
                    log_warning "○ $service 服务启动中"
                    ;;
                *)
                    log_info "? $service 服务状态未知"
                    ;;
            esac
        else
            log_error "✗ $service 服务未运行"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        log_success "所有服务运行正常"
    else
        log_warning "部分服务存在问题，请检查日志"
    fi
}

# 清理资源
cleanup() {
    log_info "清理Docker资源..."
    
    # 停止并删除容器
    docker-compose down --remove-orphans
    
    # 删除未使用的镜像
    docker image prune -f
    
    # 删除未使用的卷
    docker volume prune -f
    
    # 删除未使用的网络
    docker network prune -f
    
    log_success "资源清理完成"
}

# 备份数据
backup_data() {
    local env=${1:-$DEFAULT_ENV}
    local backup_dir="./backups/${env}/$(date +%Y%m%d_%H%M%S)"
    
    log_info "备份数据到: $backup_dir"
    
    mkdir -p "$backup_dir"
    
    # 备份数据库
    if docker ps --filter "name=${PROJECT_NAME}_redis" --filter "status=running" | grep -q "redis"; then
        log_info "备份Redis数据..."
        docker exec "${PROJECT_NAME}_redis" redis-cli BGSAVE
        sleep 2
        docker cp "${PROJECT_NAME}_redis:/data/dump.rdb" "$backup_dir/redis_dump.rdb"
    fi
    
    # 备份SQLite数据库
    if [ -d "./data" ]; then
        log_info "备份SQLite数据库..."
        cp -r ./data "$backup_dir/"
    fi
    
    # 备份配置文件
    if [ -d "./config" ]; then
        log_info "备份配置文件..."
        cp -r ./config "$backup_dir/"
    fi
    
    # 压缩备份
    tar -czf "${backup_dir}.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    rm -rf "$backup_dir"
    
    log_success "数据备份完成: ${backup_dir}.tar.gz"
}

# 恢复数据
restore_data() {
    local backup_file=$1
    
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        log_error "请提供有效的备份文件路径"
        exit 1
    fi
    
    log_info "从备份恢复数据: $backup_file"
    
    # 停止服务
    docker-compose down
    
    # 解压备份
    local temp_dir="./temp_restore"
    mkdir -p "$temp_dir"
    tar -xzf "$backup_file" -C "$temp_dir"
    
    # 恢复数据
    local backup_content=$(find "$temp_dir" -mindepth 1 -maxdepth 1 -type d | head -1)
    
    if [ -d "$backup_content/data" ]; then
        log_info "恢复SQLite数据库..."
        rm -rf ./data
        cp -r "$backup_content/data" ./
    fi
    
    if [ -d "$backup_content/config" ]; then
        log_info "恢复配置文件..."
        cp -r "$backup_content/config" ./
    fi
    
    # 清理临时文件
    rm -rf "$temp_dir"
    
    log_success "数据恢复完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态概览"
    log_info "===================="
    
    docker-compose ps
    
    echo ""
    log_info "容器资源使用情况"
    log_info "===================="
    
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 查看日志
view_logs() {
    local service=${1:-}
    
    if [ -z "$service" ]; then
        log_info "查看所有服务日志..."
        docker-compose logs -f
    else
        log_info "查看 $service 服务日志..."
        docker-compose logs -f "$service"
    fi
}

# 显示帮助信息
show_help() {
    echo "交易执行铁三角项目Docker部署脚本"
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "命令:"
    echo "  build [env]              构建Docker镜像"
    echo "  push [env]               推送镜像到仓库"
    echo "  deploy [env] [action]    部署服务"
    echo "  status                   显示服务状态"
    echo "  health                   检查服务健康状态"
    echo "  logs [service]           查看服务日志"
    echo "  backup [env]             备份数据"
    echo "  restore <backup_file>    恢复数据"
    echo "  cleanup                  清理Docker资源"
    echo ""
    echo "环境选项:"
    echo "  development  - 开发环境 (默认)"
    echo "  staging      - 预发布环境"
    echo "  production   - 生产环境"
    echo ""
    echo "部署操作:"
    echo "  up           - 启动服务 (默认)"
    echo "  down         - 停止服务"
    echo "  restart      - 重启服务"
    echo "  logs         - 查看日志"
    echo ""
    echo "示例:"
    echo "  $0 build                        # 构建开发环境镜像"
    echo "  $0 build production              # 构建生产环境镜像"
    echo "  $0 deploy                       # 部署开发环境"
    echo "  $0 deploy production up          # 部署生产环境"
    echo "  $0 deploy staging down           # 停止预发布环境"
    echo "  $0 status                       # 查看服务状态"
    echo "  $0 logs backend                 # 查看后端服务日志"
    echo "  $0 backup production            # 备份生产环境数据"
    echo "  $0 restore backup.tar.gz        # 恢复数据"
}

# 主函数
main() {
    local command=${1:-}
    
    # 检查Docker环境
    check_docker
    
    case "$command" in
        build)
            build_images "$2"
            ;;
        push)
            push_images "$2"
            ;;
        deploy)
            deploy "$2" "$3"
            ;;
        status)
            show_status
            ;;
        health)
            check_services_health
            ;;
        logs)
            view_logs "$2"
            ;;
        backup)
            backup_data "$2"
            ;;
        restore)
            restore_data "$2"
            ;;
        cleanup)
            cleanup
            ;;
        -h|--help|"")
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