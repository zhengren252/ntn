#!/bin/bash
# NeuroTrade Nexus V1.4 System Audit Script
# 基于V1.4协议的强制深度验证、基于证据的判断和脚本封装模式

set -e  # 遇到错误立即退出
set -u  # 使用未定义变量时退出

# 全局配置
AUDIT_LOG="audit_$(date +%Y%m%d_%H%M%S).log"
PASS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_result() {
    local status=$1
    local message=$2
    local timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"
    
    if [ "$status" = "PASS" ]; then
        echo -e "${timestamp} ${GREEN}PASS${NC}: $message" | tee -a $AUDIT_LOG
        ((PASS_COUNT++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${timestamp} ${RED}FAIL${NC}: $message" | tee -a $AUDIT_LOG
        ((FAIL_COUNT++))
    else
        echo -e "${timestamp} ${BLUE}INFO${NC}: $message" | tee -a $AUDIT_LOG
    fi
}

# 打印标题
print_header() {
    local title="$1"
    echo -e "\n${BLUE}========================================${NC}" | tee -a $AUDIT_LOG
    echo -e "${BLUE} $title${NC}" | tee -a $AUDIT_LOG
    echo -e "${BLUE}========================================${NC}" | tee -a $AUDIT_LOG
}

# 检查必要工具
check_prerequisites() {
    print_header "检查审计工具依赖"
    
    # 检查本地工具
    local local_tools=("curl" "jq" "ssh")
    for tool in "${local_tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            log_result "PASS" "Tool $tool is available"
        else
            log_result "FAIL" "Tool $tool is not available"
        fi
    done
    
    # 检查虚拟机Docker环境
    check_vm_docker_environment
}

# 检查虚拟机Docker环境
check_vm_docker_environment() {
    print_header "检查虚拟机Docker环境"
    
    local vm_host="192.168.1.7"  # 根据实际情况调整IP
    local vm_user="tjsga"
    
    log_result "INFO" "检查虚拟机Docker环境: $vm_user@$vm_host"
    
    # 测试SSH连接
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$vm_user@$vm_host" "echo 'SSH连接成功'" >/dev/null 2>&1; then
        log_result "PASS" "SSH连接到虚拟机成功"
        
        # 检查虚拟机上的Docker
        if ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "docker --version" >/dev/null 2>&1; then
            log_result "PASS" "虚拟机Docker可用"
            
            # 检查Docker服务状态
            if ssh -o ConnectTimeout=10 "$vm_user@$vm_host" "sudo systemctl is-active docker" | grep -q "active"; then
                log_result "PASS" "虚拟机Docker服务运行中"
            else
                log_result "FAIL" "虚拟机Docker服务未运行"
            fi
        else
            log_result "FAIL" "虚拟机Docker不可用"
        fi
    else
        log_result "FAIL" "无法SSH连接到虚拟机 $vm_user@$vm_host"
        log_result "INFO" "请确保SSH密钥已配置或虚拟机可访问"
    fi
}

# 主函数
main() {
    print_header "NeuroTrade Nexus V1.4 协议审计开始"
    log_result "INFO" "审计开始时间: $(date)"
    log_result "INFO" "审计日志文件: $AUDIT_LOG"
    
    # 检查前置条件
    check_prerequisites
    
    # 定义模块列表
    local modules=(
        "01APIForge"
        "02DataSpider"
        "03ScanPulse"
        "04OptiCore"
        "05-07TradeGuard"
        "08NeuroHub"
        "09MMS"
        "10ReviewGuard"
        "11_ASTS_Console"
        "12TACoreService"
        "13AI Strategy Assistant"
        "14Observability Center"
    )
    
    print_header "模块级静态审计"
    
    # 执行模块审计
    for module in "${modules[@]}"; do
        log_result "INFO" "开始审计模块: $module"
        
        if [ -d "$module" ]; then
            if ./audit_module.sh "$module"; then
                log_result "PASS" "模块 $module 审计通过"
            else
                log_result "FAIL" "模块 $module 审计失败"
            fi
        else
            log_result "FAIL" "模块目录 $module 不存在"
        fi
    done
    
    print_header "系统集成验证"
    
    # 执行集成测试
    if ./audit_integration.sh; then
        log_result "PASS" "系统集成验证通过"
    else
        log_result "FAIL" "系统集成验证失败"
    fi
    
    # 生成最终报告
    generate_final_report
}

# 生成最终报告
generate_final_report() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    print_header "V1.4协议审计结果摘要"
    
    echo "=== AUDIT SUMMARY ===" | tee -a $AUDIT_LOG
    echo "审计开始时间: $(date -d @$START_TIME)" | tee -a $AUDIT_LOG
    echo "审计结束时间: $(date -d @$end_time)" | tee -a $AUDIT_LOG
    echo "审计持续时间: ${duration}秒" | tee -a $AUDIT_LOG
    echo "通过项目数: $PASS_COUNT" | tee -a $AUDIT_LOG
    echo "失败项目数: $FAIL_COUNT" | tee -a $AUDIT_LOG
    
    local total_checks=$((PASS_COUNT + FAIL_COUNT))
    if [ $total_checks -gt 0 ]; then
        local pass_rate=$((PASS_COUNT * 100 / total_checks))
        echo "通过率: ${pass_rate}%" | tee -a $AUDIT_LOG
    fi
    
    if [ $FAIL_COUNT -eq 0 ]; then
        echo -e "${GREEN}OVERALL RESULT: PASS - 系统达到生产就绪标准${NC}" | tee -a $AUDIT_LOG
        exit 0
    else
        echo -e "${RED}OVERALL RESULT: FAIL - 系统存在 $FAIL_COUNT 个问题需要修复${NC}" | tee -a $AUDIT_LOG
        echo "" | tee -a $AUDIT_LOG
        echo "失败项目详情:" | tee -a $AUDIT_LOG
        grep "FAIL:" $AUDIT_LOG | tail -10
        exit 1
    fi
}

# 信号处理
trap 'echo "审计被中断"; exit 1' INT TERM

# 执行主函数
main "$@"