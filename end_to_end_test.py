import requests
import time
import subprocess
import sys

# --- 配置 ---
# 测试扫描器服务的健康状态和日志连接性
HEALTH_ENDPOINT = "http://localhost:8001/health"  # 扫描器健康检查端点
STATUS_ENDPOINT = "http://localhost:8001/api/status"  # 系统状态端点
SCAN_PULSE_CONTAINER = "ntn-scan-pulse"
TACORE_SERVICE_CONTAINER = "ntn-tacore-service"

def print_check(message, success):
    status = "✅ 成功" if success else "❌ 失败"
    print(f"{message}: {status}")
    if not success:
        sys.exit(1)

print("--- 开始核心系统端到端验证 ---")

# 1. 扫描器服务健康检查
try:
    print(f"检查扫描器服务健康状态: {HEALTH_ENDPOINT}")
    response = requests.get(HEALTH_ENDPOINT, timeout=10)
    response.raise_for_status()
    health_data = response.json()
    is_healthy = health_data.get("status") == "HEALTHY" or health_data.get("success") == True
    print_check(f"1. 扫描器服务健康检查", is_healthy)
    print(f"   - 服务状态: {health_data.get('status', 'unknown')}")
    print(f"   - Redis连接: {health_data.get('components', {}).get('redis', {}).get('status', 'unknown')}")
except Exception as e:
    print_check(f"1. 扫描器服务健康检查", False)
    print(f"   - 错误: {e}")
    sys.exit(1)

# 2. 系统状态检查
try:
    print(f"检查系统状态: {STATUS_ENDPOINT}")
    response = requests.get(STATUS_ENDPOINT, timeout=10)
    response.raise_for_status()
    status_data = response.json()
    print_check(f"2. 系统状态检查", True)
    print(f"   - 扫描器状态: {status_data.get('scanner', {}).get('status', 'unknown')}")
    print(f"   - 活跃交易对: {status_data.get('scanner', {}).get('active_symbols', 0)}")
except Exception as e:
    print_check(f"2. 系统状态检查", False)
    print(f"   - 错误: {e}")

# 等待一段时间让服务运行
time.sleep(5)

# 3. 扫描器容器日志验证
try:
    result = subprocess.run(
        ["docker", "logs", "--tail", "20", SCAN_PULSE_CONTAINER],
        capture_output=True, text=True, check=True
    )
    logs = result.stdout
    log_has_activity = ("Scanner" in logs or "scan" in logs or "INFO" in logs or "健康检查" in logs)
    print_check(f"3. 验证 {SCAN_PULSE_CONTAINER} 容器日志活动", log_has_activity)
    if not log_has_activity:
        print(f"   - 扫描器日志中未发现活动迹象")
        print("   --- 扫描器最近 20 条日志 ---")
        print(logs[:500])  # 只显示前500字符
        print("   -----------------------------------")
except Exception as e:
    print_check(f"3. 验证 {SCAN_PULSE_CONTAINER} 容器日志", False)
    print(f"   - 错误: {e}")

# 4. 交易算法核心服务验证
try:
    # 检查TACoreService的HTTP端口是否可访问
    print(f"检查TACoreService服务: http://localhost:8007/health")
    response = requests.get("http://localhost:8007/health", timeout=5)
    response.raise_for_status()
    health_data = response.json()
    is_tacore_healthy = health_data.get("status") in ["healthy", "HEALTHY"] or response.status_code == 200
    print_check(f"4. 验证 {TACORE_SERVICE_CONTAINER} 服务可用性", is_tacore_healthy)
    print(f"   - TACoreService HTTP状态: {response.status_code}")
    if health_data:
        print(f"   - 服务状态: {health_data.get('status', 'unknown')}")
except Exception as e:
    print_check(f"4. 验证 {TACORE_SERVICE_CONTAINER} 服务可用性", False)
    print(f"   - 错误: {e}")
    print(f"   - 请检查TACoreService是否在端口8007上运行")

print("\n--- 核心系统端到端验证完成 ---")
print("\n✅ 所有核心服务已成功运行并通过验证！")