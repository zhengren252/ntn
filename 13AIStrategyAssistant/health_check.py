#!/usr/bin/env python3
"""
Docker容器健康检查脚本
使用Python urllib替代curl命令进行HTTP健康检查

功能特性:
- 使用Python标准库urllib实现HTTP请求
- 支持超时控制和重试机制
- 完整的异常处理，防止脚本崩溃
- 返回标准退出码：0(健康) 或 1(不健康)
"""

import sys
import time
import urllib.request
import urllib.error
from typing import Optional


class HealthChecker:
    """健康检查器类"""
    
    def __init__(self, url: str, timeout: int = 10, retries: int = 3, retry_delay: float = 1.0):
        """
        初始化健康检查器
        
        Args:
            url: 健康检查端点URL
            timeout: 请求超时时间(秒)
            retries: 重试次数
            retry_delay: 重试间隔(秒)
        """
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
    
    def check_health(self) -> bool:
        """
        执行健康检查
        
        Returns:
            bool: True表示健康，False表示不健康
        """
        for attempt in range(self.retries + 1):
            try:
                # 创建请求对象
                request = urllib.request.Request(
                    self.url,
                    headers={
                        'User-Agent': 'Docker-HealthCheck/1.0',
                        'Accept': 'application/json, text/plain, */*'
                    }
                )
                
                # 发送HTTP请求
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    status_code = response.getcode()
                    
                    # 检查HTTP状态码
                    if 200 <= status_code < 300:
                        print(f"✅ 健康检查成功: HTTP {status_code}")
                        return True
                    else:
                        print(f"❌ 健康检查失败: HTTP {status_code}")
                        
            except urllib.error.HTTPError as e:
                print(f"❌ HTTP错误 (尝试 {attempt + 1}/{self.retries + 1}): {e.code} {e.reason}")
                
            except urllib.error.URLError as e:
                print(f"❌ URL错误 (尝试 {attempt + 1}/{self.retries + 1}): {e.reason}")
                
            except Exception as e:
                print(f"❌ 未知错误 (尝试 {attempt + 1}/{self.retries + 1}): {str(e)}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.retries:
                print(f"⏳ {self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
        
        print(f"❌ 健康检查最终失败: 已尝试 {self.retries + 1} 次")
        return False


def main():
    """
    主函数 - 解析命令行参数并执行健康检查
    """
    # 默认参数
    url = "http://localhost:8000/health"
    timeout = 10
    retries = 3
    retry_delay = 1.0
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        url = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            timeout = int(sys.argv[2])
        except ValueError:
            print("❌ 错误: 超时时间必须是整数")
            sys.exit(1)
    if len(sys.argv) > 3:
        try:
            retries = int(sys.argv[3])
        except ValueError:
            print("❌ 错误: 重试次数必须是整数")
            sys.exit(1)
    if len(sys.argv) > 4:
        try:
            retry_delay = float(sys.argv[4])
        except ValueError:
            print("❌ 错误: 重试延迟必须是数字")
            sys.exit(1)
    
    print(f"🔍 开始健康检查: {url}")
    print(f"⚙️  配置: 超时={timeout}s, 重试={retries}次, 延迟={retry_delay}s")
    
    # 创建健康检查器并执行检查
    checker = HealthChecker(url, timeout, retries, retry_delay)
    is_healthy = checker.check_health()
    
    # 返回标准退出码
    if is_healthy:
        print("✅ 容器健康状态: 正常")
        sys.exit(0)  # 健康
    else:
        print("❌ 容器健康状态: 异常")
        sys.exit(1)  # 不健康


if __name__ == "__main__":
    main()