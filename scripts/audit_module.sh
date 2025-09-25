#!/bin/bash
# NeuroTrade Nexus V1.4 Module Audit Script
# 模块级静态审计脚本 - 支持Python和Node.js项目

set -e
set -u

# 参数检查
if [ $# -ne 1 ]; then
    echo "Usage: $0 <module_directory>"
    exit 1
fi

MODULE_DIR="$1"
MODULE_LOG="module_audit_$(basename "$MODULE_DIR")_$(date +%Y%m%d_%H%M%S).log"
MODULE_PASS=0
MODULE_FAIL=0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_module_result() {
    local status=$1
    local message=$2
    local timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"
    
    if [ "$status" = "PASS" ]; then
        echo -e "${timestamp} ${GREEN}PASS${NC}: $message" | tee -a $MODULE_LOG
        ((MODULE_PASS++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${timestamp} ${RED}FAIL${NC}: $message" | tee -a $MODULE_LOG
        ((MODULE_FAIL++))
    else
        echo -e "${timestamp} ${BLUE}INFO${NC}: $message" | tee -a $MODULE_LOG
    fi
}

# 检查Python项目
audit_python_module() {
    local module_path="$1"
    
    log_module_result "INFO" "开始Python模块审计: $module_path"
    
    # 检查Python文件存在性
    if ! find "$module_path" -name "*.py" | head -1 | grep -q .; then
        log_module_result "INFO" "未发现Python文件，跳过Python审计"
        return 0
    fi
    
    # 检查requirements.txt
    if [ -f "$module_path/requirements.txt" ]; then
        log_module_result "PASS" "requirements.txt文件存在"
    else
        log_module_result "FAIL" "缺少requirements.txt文件"
    fi
    
    # Python语法检查
    log_module_result "INFO" "执行Python语法检查"
    local syntax_errors=0
    while IFS= read -r -d '' file; do
        if ! python -m py_compile "$file" 2>/dev/null; then
            log_module_result "FAIL" "Python语法错误: $file"
            ((syntax_errors++))
        fi
    done < <(find "$module_path" -name "*.py" -print0)
    
    if [ $syntax_errors -eq 0 ]; then
        log_module_result "PASS" "Python语法检查通过"
    else
        log_module_result "FAIL" "发现 $syntax_errors 个Python语法错误"
    fi
    
    # Pylint检查（如果可用）
    if command -v pylint >/dev/null 2>&1; then
        log_module_result "INFO" "执行Pylint代码质量检查"
        local pylint_score
        if pylint_score=$(find "$module_path" -name "*.py" -exec pylint {} + 2>/dev/null | grep "Your code has been rated" | tail -1 | grep -o '[0-9]\+\.[0-9]\+'); then
            if (( $(echo "$pylint_score >= 7.0" | bc -l) )); then
                log_module_result "PASS" "Pylint评分: $pylint_score/10 (>= 7.0)"
            else
                log_module_result "FAIL" "Pylint评分过低: $pylint_score/10 (< 7.0)"
            fi
        else
            log_module_result "FAIL" "Pylint检查失败"
        fi
    else
        log_module_result "FAIL" "Pylint工具未安装"
    fi
    
    # Black代码格式检查（如果可用）
    if command -v black >/dev/null 2>&1; then
        log_module_result "INFO" "执行Black代码格式检查"
        if black --check "$module_path" >/dev/null 2>&1; then
            log_module_result "PASS" "Black代码格式检查通过"
        else
            log_module_result "FAIL" "Black代码格式不符合标准"
        fi
    else
        log_module_result "FAIL" "Black工具未安装"
    fi
    
    # 安全漏洞检查（如果bandit可用）
    if command -v bandit >/dev/null 2>&1; then
        log_module_result "INFO" "执行Bandit安全检查"
        local bandit_issues
        if bandit_issues=$(bandit -r "$module_path" -f json 2>/dev/null | jq '.results | length' 2>/dev/null); then
            if [ "$bandit_issues" = "0" ]; then
                log_module_result "PASS" "Bandit安全检查通过，无安全问题"
            else
                log_module_result "FAIL" "Bandit发现 $bandit_issues 个安全问题"
            fi
        else
            log_module_result "FAIL" "Bandit安全检查执行失败"
        fi
    else
        log_module_result "FAIL" "Bandit安全工具未安装"
    fi
}

# 检查Node.js项目
audit_nodejs_module() {
    local module_path="$1"
    
    log_module_result "INFO" "开始Node.js模块审计: $module_path"
    
    # 检查package.json
    if [ -f "$module_path/package.json" ]; then
        log_module_result "PASS" "package.json文件存在"
        
        # 验证package.json格式
        if jq . "$module_path/package.json" >/dev/null 2>&1; then
            log_module_result "PASS" "package.json格式有效"
        else
            log_module_result "FAIL" "package.json格式无效"
        fi
    else
        log_module_result "INFO" "未发现package.json，跳过Node.js审计"
        return 0
    fi
    
    # 检查JavaScript/TypeScript文件
    if ! find "$module_path" \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \) | head -1 | grep -q .; then
        log_module_result "INFO" "未发现JS/TS文件"
        return 0
    fi
    
    # NPM安全审计
    if command -v npm >/dev/null 2>&1; then
        log_module_result "INFO" "执行NPM安全审计"
        cd "$module_path"
        
        if npm audit --audit-level=high --json >/dev/null 2>&1; then
            local vulnerabilities
            vulnerabilities=$(npm audit --audit-level=high --json 2>/dev/null | jq '.metadata.vulnerabilities.total' 2>/dev/null || echo "unknown")
            
            if [ "$vulnerabilities" = "0" ]; then
                log_module_result "PASS" "NPM安全审计通过，无高危漏洞"
            elif [ "$vulnerabilities" != "unknown" ]; then
                log_module_result "FAIL" "NPM发现 $vulnerabilities 个高危安全漏洞"
            else
                log_module_result "FAIL" "NPM安全审计执行失败"
            fi
        else
            log_module_result "FAIL" "NPM安全审计失败"
        fi
        
        cd - >/dev/null
    else
        log_module_result "FAIL" "NPM工具未安装"
    fi
    
    # ESLint检查（如果可用）
    if command -v eslint >/dev/null 2>&1 && [ -f "$module_path/.eslintrc.js" -o -f "$module_path/.eslintrc.json" ]; then
        log_module_result "INFO" "执行ESLint代码质量检查"
        cd "$module_path"
        
        if eslint . --format json >/dev/null 2>&1; then
            local eslint_errors
            eslint_errors=$(eslint . --format json 2>/dev/null | jq '[.[].messages[] | select(.severity == 2)] | length' 2>/dev/null || echo "unknown")
            
            if [ "$eslint_errors" = "0" ]; then
                log_module_result "PASS" "ESLint检查通过，无错误"
            elif [ "$eslint_errors" != "unknown" ]; then
                log_module_result "FAIL" "ESLint发现 $eslint_errors 个错误"
            else
                log_module_result "FAIL" "ESLint检查执行失败"
            fi
        else
            log_module_result "FAIL" "ESLint检查失败"
        fi
        
        cd - >/dev/null
    else
        log_module_result "INFO" "ESLint未配置或不可用"
    fi
}

# 检查Dockerfile
audit_dockerfile() {
    local module_path="$1"
    
    if [ -f "$module_path/Dockerfile" ]; then
        log_module_result "PASS" "Dockerfile存在"
        
        # 基本Dockerfile检查
        if grep -q "^FROM" "$module_path/Dockerfile"; then
            log_module_result "PASS" "Dockerfile包含FROM指令"
        else
            log_module_result "FAIL" "Dockerfile缺少FROM指令"
        fi
        
        # 检查是否使用了latest标签（不推荐）
        if grep -q ":latest" "$module_path/Dockerfile"; then
            log_module_result "FAIL" "Dockerfile使用了latest标签（不推荐）"
        else
            log_module_result "PASS" "Dockerfile未使用latest标签"
        fi
        
        # 检查EXPOSE指令
        if grep -q "^EXPOSE" "$module_path/Dockerfile"; then
            log_module_result "PASS" "Dockerfile包含EXPOSE指令"
        else
            log_module_result "FAIL" "Dockerfile缺少EXPOSE指令"
        fi
    else
        log_module_result "FAIL" "Dockerfile不存在"
    fi
}

# 主函数
main() {
    if [ ! -d "$MODULE_DIR" ]; then
        echo "错误: 模块目录 $MODULE_DIR 不存在"
        exit 1
    fi
    
    log_module_result "INFO" "开始模块审计: $(basename "$MODULE_DIR")"
    log_module_result "INFO" "模块路径: $MODULE_DIR"
    log_module_result "INFO" "审计日志: $MODULE_LOG"
    
    # 执行各项检查
    audit_python_module "$MODULE_DIR"
    audit_nodejs_module "$MODULE_DIR"
    audit_dockerfile "$MODULE_DIR"
    
    # 生成模块审计摘要
    echo "" | tee -a $MODULE_LOG
    echo "=== MODULE AUDIT SUMMARY ===" | tee -a $MODULE_LOG
    echo "模块: $(basename "$MODULE_DIR")" | tee -a $MODULE_LOG
    echo "通过项目: $MODULE_PASS" | tee -a $MODULE_LOG
    echo "失败项目: $MODULE_FAIL" | tee -a $MODULE_LOG
    
    if [ $MODULE_FAIL -eq 0 ]; then
        echo -e "${GREEN}模块审计结果: PASS${NC}" | tee -a $MODULE_LOG
        exit 0
    else
        echo -e "${RED}模块审计结果: FAIL (${MODULE_FAIL} 个问题)${NC}" | tee -a $MODULE_LOG
        exit 1
    fi
}

# 执行主函数
main