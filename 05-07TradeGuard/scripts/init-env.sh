#!/bin/bash

# 交易执行铁三角项目环境初始化脚本
# 用途：初始化开发、预发布、生产环境

set -e  # 遇到错误立即退出

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

# 检查必要的命令是否存在
check_dependencies() {
    log_info "检查系统依赖..."
    
    local deps=("node" "npm" "docker" "docker-compose")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_error "请安装缺少的依赖后重新运行脚本"
        exit 1
    fi
    
    log_success "系统依赖检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录结构..."
    
    local dirs=(
        "data"
        "logs"
        "backups"
        "backups/development"
        "backups/staging"
        "backups/production"
        "migrations"
        "temp"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done
    
    log_success "目录结构创建完成"
}

# 复制环境配置文件
setup_env_files() {
    log_info "设置环境配置文件..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp ".env.example" ".env"
            log_info "已从 .env.example 复制 .env 文件"
            log_warning "请编辑 .env 文件并设置正确的环境变量"
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    else
        log_info ".env 文件已存在"
    fi
    
    log_success "环境配置文件设置完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    if [ -f "package-lock.json" ]; then
        npm ci
    else
        npm install
    fi
    
    log_success "项目依赖安装完成"
}

# 初始化数据库
init_database() {
    local env=${1:-development}
    log_info "初始化 $env 环境数据库..."
    
    # 检查数据库文件是否存在
    local db_path="./data/${env}.db"
    
    if [ ! -f "$db_path" ]; then
        log_info "创建数据库文件: $db_path"
        touch "$db_path"
    fi
    
    # 运行数据库迁移
    if [ -d "migrations" ] && [ "$(ls -A migrations)" ]; then
        log_info "运行数据库迁移..."
        npm run migrate:$env || log_warning "数据库迁移脚本不存在或执行失败"
    else
        log_warning "未找到数据库迁移文件"
    fi
    
    log_success "数据库初始化完成"
}

# 启动Redis服务
start_redis() {
    log_info "启动Redis服务..."
    
    if docker ps | grep -q "redis"; then
        log_info "Redis容器已在运行"
    else
        docker-compose up -d redis
        sleep 3
        
        if docker ps | grep -q "redis"; then
            log_success "Redis服务启动成功"
        else
            log_error "Redis服务启动失败"
            exit 1
        fi
    fi
}

# 验证环境
validate_environment() {
    local env=${1:-development}
    log_info "验证 $env 环境配置..."
    
    # 检查配置文件
    local config_file="config/${env}.yaml"
    if [ ! -f "$config_file" ]; then
        log_error "配置文件不存在: $config_file"
        exit 1
    fi
    
    # 检查端口是否被占用
    local ports=("3001" "5173")
    for port in "${ports[@]}"; do
        if lsof -i :$port &> /dev/null; then
            log_warning "端口 $port 已被占用"
        fi
    done
    
    log_success "环境验证完成"
}

# 主函数
main() {
    local env=${1:-development}
    
    log_info "开始初始化交易执行铁三角项目环境: $env"
    log_info "======================================"
    
    check_dependencies
    create_directories
    setup_env_files
    install_dependencies
    init_database "$env"
    start_redis
    validate_environment "$env"
    
    log_success "======================================"
    log_success "环境初始化完成！"
    log_info "下一步操作:"
    log_info "1. 编辑 .env 文件设置环境变量"
    log_info "2. 运行 'npm run dev' 启动开发服务器"
    log_info "3. 访问 http://localhost:5173 查看应用"
}

# 显示帮助信息
show_help() {
    echo "用法: $0 [环境]"
    echo "环境选项:"
    echo "  development  - 开发环境 (默认)"
    echo "  staging      - 预发布环境"
    echo "  production   - 生产环境"
    echo ""
    echo "示例:"
    echo "  $0                    # 初始化开发环境"
    echo "  $0 development        # 初始化开发环境"
    echo "  $0 staging           # 初始化预发布环境"
    echo "  $0 production        # 初始化生产环境"
}

# 参数处理
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    development|staging|production|"")
        main "${1:-development}"
        ;;
    *)
        log_error "无效的环境参数: $1"
        show_help
        exit 1
        ;;
esac