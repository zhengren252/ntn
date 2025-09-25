#!/usr/bin/env python3
# 验收测试环境设置脚本
# Acceptance Test Environment Setup Script

import os
import sys
import subprocess
import platform
from pathlib import Path


class TestEnvironmentSetup:
    """测试环境设置类"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent
        self.python_executable = sys.executable

    def check_python_version(self) -> bool:
        """检查Python版本"""
        print("检查Python版本...")

        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"✗ Python版本过低: {version.major}.{version.minor}.{version.micro}")
            print("  需要Python 3.8或更高版本")
            return False

    def check_docker(self) -> bool:
        """检查Docker环境"""
        print("检查Docker环境...")

        try:
            # 检查Docker
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                print(f"✓ {result.stdout.strip()}")
            else:
                print("✗ Docker未安装或不可用")
                return False

            # 检查Docker Compose
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print(f"✓ {result.stdout.strip()}")
                return True
            else:
                print("✗ Docker Compose未安装或不可用")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"✗ Docker检查失败: {e}")
            return False

    def install_dependencies(self) -> bool:
        """安装测试依赖"""
        print("安装测试依赖...")

        requirements_file = self.test_root / "requirements.txt"

        if not requirements_file.exists():
            print(f"✗ 依赖文件不存在: {requirements_file}")
            return False

        try:
            # 升级pip
            subprocess.run(
                [self.python_executable, "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                timeout=60,
            )

            # 安装依赖
            subprocess.run(
                [
                    self.python_executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_file),
                ],
                check=True,
                timeout=300,
            )

            print("✓ 测试依赖安装完成")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ 依赖安装失败: {e}")
            return False
        except subprocess.TimeoutExpired:
            print("✗ 依赖安装超时")
            return False

    def create_directories(self) -> bool:
        """创建必要的目录"""
        print("创建测试目录...")

        try:
            directories = [
                self.test_root / "reports",
                self.test_root / "logs",
                self.test_root / "data",
                self.test_root / "temp",
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"✓ 创建目录: {directory}")

            return True

        except Exception as e:
            print(f"✗ 目录创建失败: {e}")
            return False

    def check_service_files(self) -> bool:
        """检查服务文件"""
        print("检查TACoreService文件...")

        required_files = [
            self.project_root / "docker-compose.yml",
            self.project_root / "src" / "main.py",
            self.project_root / "src" / "config.py",
        ]

        missing_files = []

        for file_path in required_files:
            if file_path.exists():
                print(f"✓ {file_path.name}")
            else:
                print(f"✗ 缺少文件: {file_path}")
                missing_files.append(file_path)

        if missing_files:
            print("\n请确保TACoreService项目文件完整")
            return False

        return True

    def generate_test_config(self) -> bool:
        """生成测试配置文件"""
        print("生成测试配置...")

        try:
            config_content = f"""# 测试环境配置
# Test Environment Configuration

# 服务端点
ZMQ_ENDPOINT = "tcp://localhost:5555"
HTTP_ENDPOINT = "http://localhost:8080"

# 数据库配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

SQLITE_DB_PATH = "{self.project_root}/data/tacore_service.db"

# 测试配置
TEST_TIMEOUT = 30
REQUEST_TIMEOUT = 10
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1

# 负载测试配置
CONCURRENT_REQUESTS = 10
LOAD_TEST_DURATION = 30
SCALE_TEST_WORKERS = [2, 4]

# 报告配置
REPORT_DIR = "{self.test_root}/reports"
LOG_DIR = "{self.test_root}/logs"
"""

            config_file = self.test_root / "test_config.py"
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(config_content)

            print(f"✓ 测试配置文件: {config_file}")
            return True

        except Exception as e:
            print(f"✗ 配置文件生成失败: {e}")
            return False

    def run_setup(self) -> bool:
        """运行完整设置"""
        print("=" * 60)
        print("TACoreService 验收测试环境设置")
        print(f"操作系统: {platform.system()} {platform.release()}")
        print(f"Python路径: {self.python_executable}")
        print("=" * 60)

        steps = [
            ("检查Python版本", self.check_python_version),
            ("检查Docker环境", self.check_docker),
            ("创建测试目录", self.create_directories),
            ("检查服务文件", self.check_service_files),
            ("安装测试依赖", self.install_dependencies),
            ("生成测试配置", self.generate_test_config),
        ]

        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"\n✗ 设置失败: {step_name}")
                return False

        print("\n" + "=" * 60)
        print("✓ 测试环境设置完成！")
        print("\n下一步:")
        print("1. 启动TACoreService: cd .. && docker-compose up -d")
        print("2. 运行快速测试: python quick_test.py")
        print("3. 运行完整测试: python run_tests.py")
        print("=" * 60)

        return True


def main():
    """主函数"""
    setup = TestEnvironmentSetup()

    try:
        success = setup.run_setup()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n设置被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n设置异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
