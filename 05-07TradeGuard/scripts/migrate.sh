#!/bin/bash

# 交易执行铁三角项目数据库迁移脚本
# 用途：管理数据库版本和执行迁移

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
MIGRATIONS_DIR="./migrations"
BACKUP_DIR="./backups"
DATE=$(date +"%Y%m%d_%H%M%S")

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

# 获取数据库路径
get_db_path() {
    local env=$1
    echo "./data/${env}.db"
}

# 创建迁移文件
create_migration() {
    local name=$1
    local env=${2:-development}
    
    if [ -z "$name" ]; then
        log_error "请提供迁移文件名称"
        echo "用法: $0 create <migration_name> [environment]"
        exit 1
    fi
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local filename="${timestamp}_${name}.sql"
    local filepath="${MIGRATIONS_DIR}/${filename}"
    
    # 确保迁移目录存在
    mkdir -p "$MIGRATIONS_DIR"
    
    # 创建迁移文件模板
    cat > "$filepath" << EOF
-- 迁移文件: ${filename}
-- 环境: ${env}
-- 创建时间: $(date)
-- 描述: ${name}

-- ==========================================
-- 向前迁移 (UP)
-- ==========================================

-- 在此处添加向前迁移的SQL语句
-- 例如: CREATE TABLE, ALTER TABLE, INSERT等


-- ==========================================
-- 回滚迁移 (DOWN)
-- ==========================================

-- 在此处添加回滚迁移的SQL语句
-- 例如: DROP TABLE, ALTER TABLE, DELETE等
-- 注意: 回滚语句应该能够撤销上面的向前迁移

EOF
    
    log_success "迁移文件已创建: $filepath"
    log_info "请编辑该文件并添加相应的SQL语句"
}

# 备份数据库
backup_database() {
    local env=$1
    local db_path=$(get_db_path "$env")
    
    if [ ! -f "$db_path" ]; then
        log_warning "数据库文件不存在: $db_path"
        return 0
    fi
    
    local backup_dir="${BACKUP_DIR}/${env}"
    mkdir -p "$backup_dir"
    
    local backup_file="${backup_dir}/backup_${DATE}.db"
    
    log_info "备份数据库: $db_path -> $backup_file"
    cp "$db_path" "$backup_file"
    
    # 压缩备份文件
    gzip "$backup_file"
    log_success "数据库备份完成: ${backup_file}.gz"
    
    # 清理旧备份（保留最近10个）
    find "$backup_dir" -name "backup_*.db.gz" -type f | sort -r | tail -n +11 | xargs -r rm
    log_info "已清理旧备份文件"
}

# 获取已应用的迁移
get_applied_migrations() {
    local env=$1
    local db_path=$(get_db_path "$env")
    
    if [ ! -f "$db_path" ]; then
        echo ""
        return
    fi
    
    # 检查迁移表是否存在
    local table_exists=$(sqlite3 "$db_path" "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';" 2>/dev/null || echo "")
    
    if [ -z "$table_exists" ]; then
        # 创建迁移表
        sqlite3 "$db_path" "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP);"
        echo ""
        return
    fi
    
    sqlite3 "$db_path" "SELECT version FROM schema_migrations ORDER BY version;"
}

# 获取待应用的迁移
get_pending_migrations() {
    local env=$1
    local applied_migrations=$(get_applied_migrations "$env")
    
    if [ ! -d "$MIGRATIONS_DIR" ]; then
        echo ""
        return
    fi
    
    local all_migrations=$(find "$MIGRATIONS_DIR" -name "*.sql" -type f | sort | xargs -r basename -s .sql)
    
    if [ -z "$applied_migrations" ]; then
        echo "$all_migrations"
        return
    fi
    
    # 找出未应用的迁移
    local pending=""
    for migration in $all_migrations; do
        if ! echo "$applied_migrations" | grep -q "^${migration}$"; then
            pending="$pending $migration"
        fi
    done
    
    echo "$pending" | xargs
}

# 应用单个迁移
apply_migration() {
    local env=$1
    local migration=$2
    local db_path=$(get_db_path "$env")
    local migration_file="${MIGRATIONS_DIR}/${migration}.sql"
    
    if [ ! -f "$migration_file" ]; then
        log_error "迁移文件不存在: $migration_file"
        return 1
    fi
    
    log_info "应用迁移: $migration"
    
    # 提取UP部分的SQL
    local up_sql=$(awk '/-- 向前迁移 \(UP\)/,/-- 回滚迁移 \(DOWN\)/ {if (!/-- 回滚迁移 \(DOWN\)/ && !/^--/) print}' "$migration_file")
    
    if [ -z "$up_sql" ]; then
        log_warning "迁移文件中没有找到向前迁移的SQL语句"
        return 0
    fi
    
    # 执行迁移
    echo "$up_sql" | sqlite3 "$db_path"
    
    # 记录迁移
    sqlite3 "$db_path" "INSERT INTO schema_migrations (version) VALUES ('$migration');"
    
    log_success "迁移应用成功: $migration"
}

# 回滚单个迁移
rollback_migration() {
    local env=$1
    local migration=$2
    local db_path=$(get_db_path "$env")
    local migration_file="${MIGRATIONS_DIR}/${migration}.sql"
    
    if [ ! -f "$migration_file" ]; then
        log_error "迁移文件不存在: $migration_file"
        return 1
    fi
    
    log_info "回滚迁移: $migration"
    
    # 提取DOWN部分的SQL
    local down_sql=$(awk '/-- 回滚迁移 \(DOWN\)/,EOF {if (!/-- 回滚迁移 \(DOWN\)/ && !/^--/) print}' "$migration_file")
    
    if [ -z "$down_sql" ]; then
        log_warning "迁移文件中没有找到回滚迁移的SQL语句"
        return 0
    fi
    
    # 执行回滚
    echo "$down_sql" | sqlite3 "$db_path"
    
    # 删除迁移记录
    sqlite3 "$db_path" "DELETE FROM schema_migrations WHERE version = '$migration';"
    
    log_success "迁移回滚成功: $migration"
}

# 运行迁移
run_migrations() {
    local env=${1:-development}
    local db_path=$(get_db_path "$env")
    
    log_info "开始运行 $env 环境的数据库迁移"
    
    # 确保数据库文件存在
    if [ ! -f "$db_path" ]; then
        log_info "创建数据库文件: $db_path"
        mkdir -p "$(dirname "$db_path")"
        touch "$db_path"
    fi
    
    # 备份数据库
    backup_database "$env"
    
    # 获取待应用的迁移
    local pending_migrations=$(get_pending_migrations "$env")
    
    if [ -z "$pending_migrations" ]; then
        log_info "没有待应用的迁移"
        return 0
    fi
    
    log_info "待应用的迁移: $pending_migrations"
    
    # 应用迁移
    for migration in $pending_migrations; do
        apply_migration "$env" "$migration"
    done
    
    log_success "所有迁移应用完成"
}

# 回滚迁移
rollback_migrations() {
    local env=${1:-development}
    local steps=${2:-1}
    local db_path=$(get_db_path "$env")
    
    log_info "开始回滚 $env 环境的数据库迁移 (回滚 $steps 步)"
    
    if [ ! -f "$db_path" ]; then
        log_error "数据库文件不存在: $db_path"
        return 1
    fi
    
    # 备份数据库
    backup_database "$env"
    
    # 获取已应用的迁移
    local applied_migrations=$(get_applied_migrations "$env" | sort -r)
    
    if [ -z "$applied_migrations" ]; then
        log_info "没有已应用的迁移可以回滚"
        return 0
    fi
    
    # 回滚指定步数的迁移
    local count=0
    for migration in $applied_migrations; do
        if [ $count -ge $steps ]; then
            break
        fi
        
        rollback_migration "$env" "$migration"
        count=$((count + 1))
    done
    
    log_success "迁移回滚完成"
}

# 显示迁移状态
show_status() {
    local env=${1:-development}
    
    log_info "数据库迁移状态 - 环境: $env"
    log_info "=============================="
    
    local applied_migrations=$(get_applied_migrations "$env")
    local pending_migrations=$(get_pending_migrations "$env")
    
    echo -e "${GREEN}已应用的迁移:${NC}"
    if [ -z "$applied_migrations" ]; then
        echo "  无"
    else
        echo "$applied_migrations" | while read -r migration; do
            echo "  ✓ $migration"
        done
    fi
    
    echo ""
    echo -e "${YELLOW}待应用的迁移:${NC}"
    if [ -z "$pending_migrations" ]; then
        echo "  无"
    else
        echo "$pending_migrations" | tr ' ' '\n' | while read -r migration; do
            echo "  ○ $migration"
        done
    fi
}

# 显示帮助信息
show_help() {
    echo "交易执行铁三角项目数据库迁移工具"
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "命令:"
    echo "  create <name> [env]     创建新的迁移文件"
    echo "  migrate [env]           运行待应用的迁移"
    echo "  rollback [env] [steps]  回滚迁移 (默认回滚1步)"
    echo "  status [env]            显示迁移状态"
    echo "  backup <env>            备份数据库"
    echo ""
    echo "环境选项:"
    echo "  development  - 开发环境 (默认)"
    echo "  staging      - 预发布环境"
    echo "  production   - 生产环境"
    echo ""
    echo "示例:"
    echo "  $0 create add_user_table                    # 创建迁移文件"
    echo "  $0 migrate                                  # 运行开发环境迁移"
    echo "  $0 migrate production                       # 运行生产环境迁移"
    echo "  $0 rollback development 2                   # 回滚开发环境2步"
    echo "  $0 status staging                           # 查看预发布环境状态"
    echo "  $0 backup production                        # 备份生产环境数据库"
}

# 主函数
main() {
    local command=${1:-}
    
    case "$command" in
        create)
            create_migration "$2" "$3"
            ;;
        migrate)
            run_migrations "$2"
            ;;
        rollback)
            rollback_migrations "$2" "$3"
            ;;
        status)
            show_status "$2"
            ;;
        backup)
            backup_database "$2"
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
main "$@