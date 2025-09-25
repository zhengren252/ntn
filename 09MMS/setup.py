#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场微结构仿真引擎 (MMS) 安装脚本
用于Python包的安装和分发

作者: NeuroTrade Nexus 开发团队
版本: 1.0.0
创建时间: 2024-12-01
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# 确保Python版本
if sys.version_info < (3, 8):
    raise RuntimeError("Python 3.8+ is required")

# 项目根目录
HERE = Path(__file__).parent.absolute()


# 读取README文件
def read_readme():
    readme_path = HERE / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Market Microstructure Simulation Engine"


# 读取requirements文件
def read_requirements(filename):
    requirements_path = HERE / filename
    if requirements_path.exists():
        with open(requirements_path, "r", encoding="utf-8") as f:
            return [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    return []


# 获取版本信息
def get_version():
    version_file = HERE / "src" / "__init__.py"
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    return "1.0.0"


# 项目元数据
NAME = "market-microstructure-simulation"
VERSION = get_version()
DESCRIPTION = (
    "Market Microstructure Simulation Engine for High-Frequency Trading Research"
)
LONG_DESCRIPTION = read_readme()
AUTHOR = "NeuroTrade Nexus Team"
AUTHOR_EMAIL = "dev@neurotrade-nexus.com"
URL = "https://github.com/neurotrade-nexus/market-microstructure-simulation"
LICENSE = "MIT"

# 分类信息
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Financial and Insurance Industry",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Office/Business :: Financial :: Investment",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Framework :: FastAPI",
    "Framework :: AsyncIO",
]

# 关键词
KEYWORDS = [
    "market microstructure",
    "high frequency trading",
    "simulation",
    "market making",
    "arbitrage",
    "financial modeling",
    "quantitative finance",
    "trading algorithms",
    "order book",
    "limit order book",
    "market data",
    "backtesting",
    "risk management",
    "portfolio optimization",
]

# 依赖包
INSTALL_REQUIRES = read_requirements("requirements.txt")

# 开发依赖
EXTRAS_REQUIRE = {
    "dev": [
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
    ],
    "docs": [
        "sphinx>=7.2.6",
        "sphinx-rtd-theme>=1.3.0",
        "sphinx-autodoc-typehints>=1.25.2",
        "myst-parser>=2.0.0",
    ],
    "monitoring": [
        "prometheus-client>=0.19.0",
        "grafana-api>=1.0.3",
        "elasticsearch>=8.11.0",
    ],
    "performance": [
        "cython>=3.0.6",
        "numba>=0.58.1",
        "line-profiler>=4.1.1",
        "memory-profiler>=0.61.0",
    ],
    "ml": [
        "tensorflow>=2.15.0",
        "torch>=2.1.0",
        "xgboost>=2.0.2",
        "lightgbm>=4.1.0",
    ],
}

# 所有额外依赖
EXTRAS_REQUIRE["all"] = list(
    set(dep for deps in EXTRAS_REQUIRE.values() for dep in deps)
)

# 入口点
ENTRY_POINTS = {
    "console_scripts": [
        "mms-server=src.api.main:main",
        "mms-worker=src.core.worker:main",
        "mms-balancer=src.core.load_balancer:main",
        "mms-init-db=scripts.init_database:main",
        "mms-setup=scripts.setup_dev:main",
    ],
}

# 包数据
PACKAGE_DATA = {
    "src": [
        "*.yaml",
        "*.yml",
        "*.json",
        "*.sql",
        "*.txt",
    ],
}

# 数据文件
DATA_FILES = [
    ("config", ["config/config.example.yaml"]),
    (
        "scripts",
        [
            "scripts/init_database.py",
            "scripts/setup_dev.py",
            "scripts/start_services.py",
        ],
    ),
    ("docs", ["README.md", "LICENSE"]),
]

# Python要求
PYTHON_REQUIRES = ">=3.8"

# 项目URL
PROJECT_URLS = {
    "Documentation": "https://mms.neurotrade-nexus.com/docs",
    "Source": "https://github.com/neurotrade-nexus/market-microstructure-simulation",
    "Tracker": "https://github.com/neurotrade-nexus/market-microstructure-simulation/issues",
    "Changelog": "https://github.com/neurotrade-nexus/market-microstructure-simulation/blob/main/CHANGELOG.md",
}


# 自定义命令
class CustomCommand:
    """自定义安装命令基类"""

    def run_command(self, command):
        """运行系统命令"""
        import subprocess

        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"命令执行失败: {e}")
            sys.exit(1)


class DevelopCommand(CustomCommand):
    """开发环境安装命令"""

    description = "安装开发环境"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print("设置开发环境...")
        self.run_command("python scripts/setup_dev.py")
        print("开发环境设置完成")


class TestCommand(CustomCommand):
    """测试命令"""

    description = "运行测试"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print("运行测试...")
        self.run_command("python -m pytest tests/ -v")


class LintCommand(CustomCommand):
    """代码检查命令"""

    description = "运行代码检查"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print("运行代码检查...")
        self.run_command("black src/ tests/ scripts/")
        self.run_command("isort src/ tests/ scripts/ --profile black")
        self.run_command("flake8 src/ tests/ scripts/")
        self.run_command("mypy src/")


# 自定义命令映射
CMDCLASS = {
    "develop": DevelopCommand,
    "test": TestCommand,
    "lint": LintCommand,
}

# 主要设置
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    project_urls=PROJECT_URLS,
    license=LICENSE,
    classifiers=CLASSIFIERS,
    keywords=" ".join(KEYWORDS),
    # 包配置
    packages=find_packages(exclude=["tests*", "docs*", "scripts*"]),
    package_dir={"": "."},
    package_data=PACKAGE_DATA,
    data_files=DATA_FILES,
    include_package_data=True,
    # 依赖配置
    python_requires=PYTHON_REQUIRES,
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    # 入口点
    entry_points=ENTRY_POINTS,
    # 自定义命令
    cmdclass=CMDCLASS,
    # 其他配置
    zip_safe=False,
    platforms=["any"],
    # 测试配置
    test_suite="tests",
    # 元数据
    options={
        "build_scripts": {
            "executable": "/usr/bin/env python3",
        },
    },
)

# 安装后提示
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("市场微结构仿真引擎 (MMS) 安装完成!")
    print("=" * 60)
    print("\n下一步:")
    print("1. 复制配置文件: cp config/config.example.yaml config/config.yaml")
    print("2. 编辑配置文件: vim config/config.yaml")
    print("3. 初始化数据库: mms-init-db")
    print("4. 启动服务: mms-server")
    print("\n文档: https://mms.neurotrade-nexus.com/docs")
    print(
        "支持: https://github.com/neurotrade-nexus/market-microstructure-simulation/issues"
    )
    print("=" * 60)
