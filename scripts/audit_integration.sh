#!/bin/bash
# NeuroTrade Nexus V1.4 Integration Audit Script
# 系统集成验证脚本 - 容器健康检查和服务端点验证

set -e
set -u

INTEGRATION_LOG="integration_audit_$(date +%Y%m%d_%H%M%S).log"
INTEGRATION_PASS=0
INTEGRATION_FAIL=0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_integration_result() {
    local status=$1
    local message=$2
    local timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"
    
    if [ "$status" = "PASS" ]; then
        echo -e "${timestamp} ${GREEN}PASS${NC}: $message" | tee -a $INTEGRATION_LOG
        ((INTEGRATION_PASS++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${timestamp} ${RED}FAIL${NC}: $message" | tee -a $INTEGRATION_LOG
        ((INTEGRATION_FAIL++))
    else
        echo -e "${timestamp} ${BLUE}INFO${NC}: $message" | tee -a $INTEGRATION_LOG
    fi
}

# 检查Docker环境
check_docker_environment() {
    log_integration_result "INFO" "检查虚拟机Docker环境"
    
    local vm_host="192.168.1.7"  # 根据实际情况调整IP
    local vm_user="tjsga"
    
    # 检查SSH连接
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$vm_user@$vm_host" "echo 'SSH连接测试'" >/dev/null 2>&1; then
        log_integration_result "FAIL" "无法SSH连接到虚拟机 $vm_user@$vm_host"
        return 1
    fi
    
    log_integration_result "PASS" "SSH连接到虚拟机成功"
    
    # 检查虚拟机Docker
    if ! ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "docker info" >/dev/null 2>&1; then
        log_integration_result "FAIL" "虚拟机Docker守护进程未运行或不可用"
        return 1
    fi
    
    log_integration_result "PASS" "虚拟机Docker环境可用"
    
    # 检查虚拟机docker-compose
    if ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "command -v docker-compose" >/dev/null 2>&1; then
        log_integration_result "PASS" "虚拟机docker-compose可用"
    else
        log_integration_result "FAIL" "虚拟机docker-compose未安装"
    fi
}

# 检查容器状态
check_container_health() {
    log_integration_result "INFO" "检查虚拟机容器健康状态"
    
    local vm_host="192.168.1.7"
    local vm_user="tjsga"
    local vm_project_path="~/projects"  # 虚拟机上的项目路径
    
    # 检查虚拟机上的docker-compose.yml文件
    if ! ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "[ -f $vm_project_path/docker-compose.yml ] || [ -f $vm_project_path/docker-compose.prod.yml ]" 2>/dev/null; then
        log_integration_result "FAIL" "虚拟机上未找到docker-compose配置文件"
        return 1
    fi
    
    local compose_file="docker-compose.yml"
    if ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "[ -f $vm_project_path/docker-compose.prod.yml ]" 2>/dev/null; then
        compose_file="docker-compose.prod.yml"
    fi
    
    log_integration_result "INFO" "使用虚拟机配置文件: $compose_file"
    
    # 检查虚拟机上的容器是否运行
    local running_containers
    running_containers=$(ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "cd $vm_project_path && docker-compose -f $compose_file ps -q 2>/dev/null | wc -l" 2>/dev/null || echo "0")
    
    if [ "$running_containers" -gt 0 ]; then
        log_integration_result "PASS" "虚拟机上发现 $running_containers 个运行中的容器"
        
        # 检查每个容器的健康状态
        local container_ids
        container_ids=$(ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "cd $vm_project_path && docker-compose -f $compose_file ps -q" 2>/dev/null)
        
        if [ -n "$container_ids" ]; then
            while IFS= read -r container_id; do
                if [ -n "$container_id" ]; then
                    local container_name
                    container_name=$(ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "docker inspect --format='{{.Name}}' $container_id | sed 's/^\///'" 2>/dev/null)
                    
                    local container_status
                    container_status=$(ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "docker inspect --format='{{.State.Status}}' $container_id" 2>/dev/null)
                    
                    if [ "$container_status" = "running" ]; then
                        log_integration_result "PASS" "虚拟机容器 $container_name 状态: running"
                        
                        # 检查健康检查状态（如果配置了）
                        local health_status
                        health_status=$(ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "docker inspect --format='{{.State.Health.Status}}' $container_id 2>/dev/null || echo 'none'" 2>/dev/null)
                        
                        if [ "$health_status" = "healthy" ]; then
                            log_integration_result "PASS" "虚拟机容器 $container_name 健康检查: healthy"
                        elif [ "$health_status" = "unhealthy" ]; then
                            log_integration_result "FAIL" "虚拟机容器 $container_name 健康检查: unhealthy"
                        else
                            log_integration_result "INFO" "虚拟机容器 $container_name 未配置健康检查"
                        fi
                    else
                        log_integration_result "FAIL" "虚拟机容器 $container_name 状态: $container_status"
                    fi
                fi
            done <<< "$container_ids"
        fi
    else
        log_integration_result "FAIL" "虚拟机上未发现运行中的容器"
    fi
}

# 检查网络连通性
check_network_connectivity() {
    log_integration_result "INFO" "检查虚拟机网络连通性"
    
    local vm_host="192.168.1.7"
    local vm_user="tjsga"
    
    # 定义需要检查的虚拟机服务端点
    local endpoints=(
        "http://192.168.1.7:8080/health"  # API Gateway
        "http://192.168.1.7:8081/health"  # Data Spider
        "http://192.168.1.7:8082/health"  # Scan Pulse
        "http://192.168.1.7:8083/health"  # OptiCore
        "http://192.168.1.7:8084/health"  # TradeGuard
        "http://192.168.1.7:8085/health"  # NeuroHub
        "http://192.168.1.7:8086/health"  # MMS
        "http://192.168.1.7:8087/health"  # Review Guard
        "http://192.168.1.7:8088/health"  # ASTS Console
        "http://192.168.1.7:8089/health"  # TACore Service
        "http://192.168.1.7:8090/health"  # AI Strategy Assistant
        "http://192.168.1.7:8091/health"  # Observability Center
    )
    
    local reachable_endpoints=0
    local total_endpoints=${#endpoints[@]}
    
    for endpoint in "${endpoints[@]}"; do
        log_integration_result "INFO" "测试虚拟机端点: $endpoint"
        
        if curl -s -f --max-time 10 "$endpoint" >/dev/null 2>&1; then
            log_integration_result "PASS" "虚拟机端点可达: $endpoint"
            ((reachable_endpoints++))
        else
            # 尝试基本连接测试
            local port
            port=$(echo "$endpoint" | grep -o ':[0-9]\+' | sed 's/://')
            
            if nc -z "$vm_host" "$port" 2>/dev/null; then
                log_integration_result "FAIL" "虚拟机端点 $endpoint 端口开放但健康检查失败"
            else
                log_integration_result "FAIL" "虚拟机端点不可达: $endpoint"
            fi
        fi
    done
    
    local connectivity_rate=$((reachable_endpoints * 100 / total_endpoints))
    log_integration_result "INFO" "端点连通率: ${connectivity_rate}% ($reachable_endpoints/$total_endpoints)"
    
    if [ $connectivity_rate -ge 80 ]; then
        log_integration_result "PASS" "网络连通性测试通过 (>= 80%)"
    else
        log_integration_result "FAIL" "网络连通性测试失败 (< 80%)"
    fi
}

# 检查API功能
check_api_functionality() {
    log_integration_result "INFO" "检查虚拟机API功能"
    
    local vm_host="192.168.1.7"
    local api_base="http://$vm_host:8080"
    
    # 检查虚拟机API Gateway根路径
    if curl -s --max-time 5 "$api_base/" > /dev/null 2>&1; then
        log_integration_result "PASS" "虚拟机API Gateway根路径可访问"
    else
        log_integration_result "FAIL" "虚拟机API Gateway根路径不可访问"
    fi
    
    # 检查版本信息
    local version_response
    version_response=$(curl -s --max-time 5 "$api_base/version" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$version_response" ]; then
        log_integration_result "PASS" "虚拟机版本信息API可用: $version_response"
    else
        log_integration_result "FAIL" "虚拟机版本信息API不可用"
    fi
    
    # 检查认证端点
    local auth_response
    auth_response=$(curl -s --max-time 5 -w "%{http_code}" "$api_base/auth/status" 2>/dev/null)
    if [[ "$auth_response" =~ [0-9]{3}$ ]]; then
        local http_code="${auth_response: -3}"
        if [ "$http_code" = "200" ] || [ "$http_code" = "401" ]; then
            log_integration_result "PASS" "虚拟机认证端点响应正常 (HTTP $http_code)"
        else
            log_integration_result "FAIL" "虚拟机认证端点响应异常 (HTTP $http_code)"
        fi
    else
        log_integration_result "FAIL" "虚拟机认证端点无响应"
    fi
}

# 检查数据库连接
check_database_connectivity() {
    log_integration_result "INFO" "检查数据库连接"
    
    # 检查Redis连接
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
            log_integration_result "PASS" "Redis连接正常"
        else
            log_integration_result "FAIL" "Redis连接失败"
        fi
    else
        log_integration_result "INFO" "Redis客户端未安装，跳过Redis检查"
    fi
    
    # 检查PostgreSQL连接（如果配置了）
    if command -v psql >/dev/null 2>&1; then
        if PGPASSWORD=password psql -h localhost -U postgres -d neurotrade -c "SELECT 1;" >/dev/null 2>&1; then
            log_integration_result "PASS" "PostgreSQL连接正常"
        else
            log_integration_result "FAIL" "PostgreSQL连接失败"
        fi
    else
        log_integration_result "INFO" "PostgreSQL客户端未安装，跳过数据库检查"
    fi
}

# 检查日志输出
check_log_output() {
    log_integration_result "INFO" "检查系统日志输出"
    
    # 检查Docker容器日志
    local compose_file="docker-compose.yml"
    if [ -f "docker-compose.prod.yml" ]; then
        compose_file="docker-compose.prod.yml"
    fi
    
    if [ -f "$compose_file" ]; then
        local error_count=0
        
        # 检查最近的错误日志
        while IFS= read -r container_id; do
            if [ -n "$container_id" ]; then
                local container_name
                container_name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's/^\///')
                
                local error_logs
                error_logs=$(docker logs "$container_id" --since="5m" 2>&1 | grep -i "error\|exception\|fatal" | wc -l)
                
                if [ "$error_logs" -eq 0 ]; then
                    log_integration_result "PASS" "容器 $container_name 近期无错误日志"
                else
                    log_integration_result "FAIL" "容器 $container_name 发现 $error_logs 条错误日志"
                    ((error_count += error_logs))
                fi
            fi
        done < <(docker-compose -f "$compose_file" ps -q)
        
        if [ $error_count -eq 0 ]; then
            log_integration_result "PASS" "系统日志检查通过，无错误"
        else
            log_integration_result "FAIL" "系统日志检查发现 $error_count 个错误"
        fi
    else
        log_integration_result "FAIL" "未找到docker-compose配置文件"
    fi
}

# 性能基准测试
performance_benchmark() {
    log_integration_result "INFO" "执行性能基准测试"
    
    local api_base="http://localhost:8000"
    
    # 简单的响应时间测试
    local response_time
    response_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time 10 "$api_base/health" 2>/dev/null || echo "timeout")
    
    if [ "$response_time" != "timeout" ]; then
        local response_ms
        response_ms=$(echo "$response_time * 1000" | bc -l | cut -d. -f1)
        
        if [ "$response_ms" -lt 1000 ]; then
            log_integration_result "PASS" "API响应时间: ${response_ms}ms (< 1000ms)"
        else
            log_integration_result "FAIL" "API响应时间过慢: ${response_ms}ms (>= 1000ms)"
        fi
    else
        log_integration_result "FAIL" "API响应超时"
    fi
}

# 主函数
main() {
    log_integration_result "INFO" "开始系统集成验证"
    log_integration_result "INFO" "集成测试日志: $INTEGRATION_LOG"
    
    # 执行各项集成测试
    check_docker_environment
    check_container_health
    check_network_connectivity
    check_api_functionality
    check_database_connectivity
    check_log_output
    performance_benchmark
    
    # 生成集成测试摘要
    echo "" | tee -a $INTEGRATION_LOG
    echo "=== INTEGRATION AUDIT SUMMARY ===" | tee -a $INTEGRATION_LOG
    echo "通过项目: $INTEGRATION_PASS" | tee -a $INTEGRATION_LOG
    echo "失败项目: $INTEGRATION_FAIL" | tee -a $INTEGRATION_LOG
    
    local total_checks=$((INTEGRATION_PASS + INTEGRATION_FAIL))
    if [ $total_checks -gt 0 ]; then
        local pass_rate=$((INTEGRATION_PASS * 100 / total_checks))
        echo "通过率: ${pass_rate}%" | tee -a $INTEGRATION_LOG
    fi
    
    if [ $INTEGRATION_FAIL -eq 0 ]; then
        echo -e "${GREEN}集成测试结果: PASS${NC}" | tee -a $INTEGRATION_LOG
        exit 0
    else
        echo -e "${RED}集成测试结果: FAIL (${INTEGRATION_FAIL} 个问题)${NC}" | tee -a $INTEGRATION_LOG
        exit 1
    fi
}

# 执行主函数
main