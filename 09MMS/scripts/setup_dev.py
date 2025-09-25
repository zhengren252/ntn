#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) - 开发环境设置脚本
用于自动安装和配置项目依赖

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import argparse
import json
from typing import List, Dict, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class DevEnvironmentSetup:
    """开发环境设置器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.system = platform.system().lower()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        # 依赖目录配置
        self.core_lib_dir = Path("D:/yilai/core_lib")
        self.temp_lib_dir = Path("D:/yilai/temp_lib")

        # 确保依赖目录存在
        self.core_lib_dir.mkdir(parents=True, exist_ok=True)
        self.temp_lib_dir.mkdir(parents=True, exist_ok=True)

        # 版本日志文件
        self.version_log_file = self.core_lib_dir / "version_log.json"

        # 加载现有版本日志
        self.version_log = self._load_version_log()

    def _load_version_log(self) -> Dict:
        """加载版本日志"""
        if self.version_log_file.exists():
            try:
                with open(self.version_log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self._log(f"加载版本日志失败: {e}")

        return {
            "created_at": self._get_timestamp(),
            "python_version": self.python_version,
            "system": self.system,
            "installations": [],
            "updates": [],
        }

    def _save_version_log(self):
        """保存版本日志"""
        try:
            with open(self.version_log_file, "w", encoding="utf-8") as f:
                json.dump(self.version_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"保存版本日志失败: {e}")

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{level}] {message}")

    def _run_command(self, command: List[str], cwd: Optional[Path] = None) -> bool:
        """执行命令"""
        try:
            self._log(f"执行命令: {' '.join(command)}")

            result = subprocess.run(
                command,
                cwd=cwd or PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )

            if self.verbose and result.stdout:
                print(result.stdout)

            return True

        except subprocess.CalledProcessError as e:
            self._log(f"命令执行失败: {e}", "ERROR")
            if e.stderr:
                self._log(f"错误输出: {e.stderr}", "ERROR")
            return False
        except Exception as e:
            self._log(f"执行命令时发生异常: {e}", "ERROR")
            return False

    def check_python_version(self) -> bool:
        """检查Python版本"""
        self._log("检查Python版本...")

        min_version = (3, 8)
        current_version = (sys.version_info.major, sys.version_info.minor)

        if current_version < min_version:
            self._log(
                f"Python版本过低: {self.python_version}, 需要 >= {min_version[0]}.{min_version[1]}",
                "ERROR",
            )
            return False

        self._log(f"Python版本检查通过: {self.python_version}")
        return True

    def check_system_dependencies(self) -> bool:
        """检查系统依赖"""
        self._log("检查系统依赖...")

        required_tools = {"git": "Git版本控制系统", "pip": "Python包管理器"}

        missing_tools = []

        for tool, description in required_tools.items():
            if not shutil.which(tool):
                missing_tools.append(f"{tool} ({description})")
            else:
                self._log(f"✓ {tool} 已安装")

        if missing_tools:
            self._log(f"缺少必要工具: {', '.join(missing_tools)}", "ERROR")
            return False

        return True

    def setup_virtual_environment(self) -> bool:
        """设置虚拟环境"""
        self._log("设置虚拟环境...")

        venv_path = PROJECT_ROOT / "venv"

        # 检查虚拟环境是否已存在
        if venv_path.exists():
            self._log("虚拟环境已存在")
            return True

        # 创建虚拟环境
        if not self._run_command([sys.executable, "-m", "venv", str(venv_path)]):
            return False

        self._log("虚拟环境创建成功")

        # 记录到版本日志
        self.version_log["installations"].append(
            {
                "timestamp": self._get_timestamp(),
                "type": "virtual_environment",
                "path": str(venv_path),
                "python_version": self.python_version,
            }
        )

        return True

    def install_core_dependencies(self) -> bool:
        """安装核心依赖"""
        self._log("安装核心依赖...")

        # 核心依赖列表
        core_packages = [
            "fastapi>=0.104.1",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.5.0",
            "sqlalchemy>=2.0.23",
            "aiosqlite>=0.19.0",
            "redis>=5.0.1",
            "pyzmq>=25.1.1",
            "numpy>=1.24.3",
            "pandas>=2.1.4",
            "scipy>=1.11.4",
            "scikit-learn>=1.3.2",
            "pyyaml>=6.0.1",
            "python-multipart>=0.0.6",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "python-dotenv>=1.0.0",
        ]

        # 安装到核心库目录
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(self.core_lib_dir),
            "--upgrade",
        ] + core_packages

        if not self._run_command(install_cmd):
            return False

        # 记录安装信息
        for package in core_packages:
            self.version_log["installations"].append(
                {
                    "timestamp": self._get_timestamp(),
                    "type": "core_package",
                    "package": package,
                    "target": str(self.core_lib_dir),
                }
            )

        self._log("核心依赖安装完成")
        return True

    def install_dev_dependencies(self) -> bool:
        """安装开发依赖"""
        self._log("安装开发依赖...")

        # 开发依赖列表
        dev_packages = [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
            "bandit>=1.7.5",
            "safety>=2.3.5",
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=1.3.0",
        ]

        # 安装到临时库目录
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(self.temp_lib_dir),
            "--upgrade",
        ] + dev_packages

        if not self._run_command(install_cmd):
            return False

        # 记录安装信息
        for package in dev_packages:
            self.version_log["installations"].append(
                {
                    "timestamp": self._get_timestamp(),
                    "type": "dev_package",
                    "package": package,
                    "target": str(self.temp_lib_dir),
                }
            )

        self._log("开发依赖安装完成")
        return True

    def install_requirements(self) -> bool:
        """从requirements.txt安装依赖"""
        requirements_file = PROJECT_ROOT / "requirements.txt"

        if not requirements_file.exists():
            self._log("requirements.txt 文件不存在，跳过")
            return True

        self._log("从requirements.txt安装依赖...")

        # 安装到核心库目录
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(self.core_lib_dir),
            "-r",
            str(requirements_file),
            "--upgrade",
        ]

        if not self._run_command(install_cmd):
            return False

        # 记录安装信息
        self.version_log["installations"].append(
            {
                "timestamp": self._get_timestamp(),
                "type": "requirements_file",
                "file": str(requirements_file),
                "target": str(self.core_lib_dir),
            }
        )

        self._log("requirements.txt 依赖安装完成")
        return True

    def setup_pre_commit_hooks(self) -> bool:
        """设置pre-commit钩子"""
        self._log("设置pre-commit钩子...")

        pre_commit_config = PROJECT_ROOT / ".pre-commit-config.yaml"

        if not pre_commit_config.exists():
            # 创建pre-commit配置文件
            config_content = """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
"""

            with open(pre_commit_config, "w", encoding="utf-8") as f:
                f.write(config_content)

            self._log("创建了pre-commit配置文件")

        # 安装pre-commit钩子
        if not self._run_command(["pre-commit", "install"]):
            self._log("pre-commit钩子安装失败，可能需要手动安装", "WARNING")
            return True  # 不阻止整个安装过程

        self._log("pre-commit钩子设置完成")
        return True

    def create_config_files(self) -> bool:
        """创建配置文件"""
        self._log("创建配置文件...")

        # 创建.env文件（如果不存在）
        env_file = PROJECT_ROOT / ".env"
        if not env_file.exists():
            env_content = """
# 市场微结构仿真引擎环境配置

# 应用配置
APP_NAME=Market Microstructure Simulation Engine
APP_VERSION=1.0.0
DEBUG=true
ENVIRONMENT=development

# 服务器配置
HOST=127.0.0.1
PORT=8000
WORKERS=1

# 数据库配置
DATABASE_URL=sqlite:///./data/mms.db

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ZeroMQ配置
ZMQ_FRONTEND_PORT=5555
ZMQ_BACKEND_PORT=5556
ZMQ_MONITOR_PORT=5557

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/mms.log

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 性能配置
MAX_WORKERS=4
TASK_TIMEOUT=300
CACHE_TTL=3600
"""

            with open(env_file, "w", encoding="utf-8") as f:
                f.write(env_content)

            self._log("创建了.env配置文件")

        # 创建pytest配置（如果不存在）
        pytest_ini = PROJECT_ROOT / "pytest.ini"
        if not pytest_ini.exists():
            self._log("pytest.ini已存在，跳过创建")

        return True

    def verify_installation(self) -> bool:
        """验证安装"""
        self._log("验证安装...")

        # 检查关键包是否可以导入
        test_imports = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "sqlalchemy",
            "redis",
            "zmq",
            "numpy",
            "pandas",
            "pytest",
        ]

        failed_imports = []

        for package in test_imports:
            try:
                # 临时添加依赖目录到Python路径
                if str(self.core_lib_dir) not in sys.path:
                    sys.path.insert(0, str(self.core_lib_dir))
                if str(self.temp_lib_dir) not in sys.path:
                    sys.path.insert(0, str(self.temp_lib_dir))

                __import__(package)
                self._log(f"✓ {package} 导入成功")
            except ImportError as e:
                failed_imports.append(f"{package}: {e}")
                self._log(f"✗ {package} 导入失败: {e}", "ERROR")

        if failed_imports:
            self._log(f"以下包导入失败: {failed_imports}", "ERROR")
            return False

        self._log("安装验证通过")
        return True

    def run_setup(self, skip_dev: bool = False, skip_pre_commit: bool = False) -> bool:
        """运行完整设置"""
        self._log("开始设置开发环境...")

        steps = [
            ("检查Python版本", self.check_python_version),
            ("检查系统依赖", self.check_system_dependencies),
            ("设置虚拟环境", self.setup_virtual_environment),
            ("安装核心依赖", self.install_core_dependencies),
            ("安装requirements.txt", self.install_requirements),
            ("创建配置文件", self.create_config_files),
            ("验证安装", self.verify_installation),
        ]

        if not skip_dev:
            steps.insert(-1, ("安装开发依赖", self.install_dev_dependencies))

        if not skip_pre_commit:
            steps.insert(-1, ("设置pre-commit钩子", self.setup_pre_commit_hooks))

        for step_name, step_func in steps:
            self._log(f"\n=== {step_name} ===")
            if not step_func():
                self._log(f"{step_name} 失败", "ERROR")
                return False
            self._log(f"{step_name} 完成")

        # 保存版本日志
        self._save_version_log()

        self._log("\n开发环境设置完成！")
        self._log("\n下一步:")
        self._log("1. 复制 config/config.example.yaml 到 config/config.yaml 并修改配置")
        self._log("2. 运行 python scripts/init_database.py 初始化数据库")
        self._log("3. 运行 python scripts/start_services.py 启动服务")

        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="市场微结构仿真引擎开发环境设置")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--skip-dev", action="store_true", help="跳过开发依赖安装")
    parser.add_argument("--skip-pre-commit", action="store_true", help="跳过pre-commit设置")

    args = parser.parse_args()

    # 创建设置器
    setup = DevEnvironmentSetup(verbose=args.verbose)

    try:
        success = setup.run_setup(
            skip_dev=args.skip_dev, skip_pre_commit=args.skip_pre_commit
        )
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n设置被中断")
        return 0
    except Exception as e:
        print(f"设置过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
