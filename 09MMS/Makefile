# 市场微结构仿真引擎 (MMS) Makefile
# 用于简化常用的开发和部署命令

# 变量定义
PYTHON := python
PIP := pip
PYTEST := pytest
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy

# 项目目录
SRC_DIR := src
TEST_DIR := tests
SCRIPTS_DIR := scripts
CONFIG_DIR := config
DATA_DIR := data
LOGS_DIR := logs

# 配置文件
CONFIG_FILE := $(CONFIG_DIR)/config.yaml
CONFIG_EXAMPLE := $(CONFIG_DIR)/config.example.yaml
ENV_FILE := .env
REQUIREMENTS := requirements.txt

# 默认目标
.PHONY: help
help:
	@echo "市场微结构仿真引擎 (MMS) - 可用命令:"
	@echo ""
	@echo "开发环境:"
	@echo "  setup          - 设置开发环境"
	@echo "  install        - 安装依赖包"
	@echo "  install-dev    - 安装开发依赖"
	@echo "  clean          - 清理临时文件"
	@echo ""
	@echo "数据库:"
	@echo "  init-db        - 初始化数据库"
	@echo "  reset-db       - 重置数据库"
	@echo "  verify-db      - 验证数据库"
	@echo ""
	@echo "服务管理:"
	@echo "  start          - 启动所有服务"
	@echo "  stop           - 停止所有服务"
	@echo "  restart        - 重启所有服务"
	@echo "  status         - 查看服务状态"
	@echo "  api            - 启动API服务器"
	@echo "  worker         - 启动工作进程"
	@echo "  balancer       - 启动负载均衡器"
	@echo ""
	@echo "测试:"
	@echo "  test           - 运行所有测试"
	@echo "  test-unit      - 运行单元测试"
	@echo "  test-integration - 运行集成测试"
	@echo "  test-cov       - 运行测试并生成覆盖率报告"
	@echo "  test-watch     - 监视文件变化并运行测试"
	@echo ""
	@echo "代码质量:"
	@echo "  lint           - 运行所有代码检查"
	@echo "  format         - 格式化代码"
	@echo "  type-check     - 类型检查"
	@echo "  security       - 安全检查"
	@echo ""
	@echo "文档:"
	@echo "  docs           - 生成文档"
	@echo "  docs-serve     - 启动文档服务器"
	@echo ""
	@echo "部署:"
	@echo "  build          - 构建项目"
	@echo "  package        - 打包项目"
	@echo "  docker-build   - 构建Docker镜像"
	@echo "  docker-run     - 运行Docker容器"

# 开发环境设置
.PHONY: setup
setup:
	@echo "设置开发环境..."
	$(PYTHON) $(SCRIPTS_DIR)/setup_dev.py --verbose
	@echo "开发环境设置完成"

.PHONY: install
install:
	@echo "安装依赖包..."
	$(PIP) install -r $(REQUIREMENTS)

.PHONY: install-dev
install-dev:
	@echo "安装开发依赖..."
	$(PIP) install -r $(REQUIREMENTS)
	$(PIP) install pytest pytest-asyncio pytest-cov pytest-mock black isort flake8 mypy pre-commit bandit safety

.PHONY: clean
clean:
	@echo "清理临时文件..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type f -name ".coverage" -delete
	@find . -type d -name "htmlcov" -exec rm -rf {} +
	@find . -type d -name "dist" -exec rm -rf {} +
	@find . -type d -name "build" -exec rm -rf {} +
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "清理完成"

# 数据库管理
.PHONY: init-db
init-db:
	@echo "初始化数据库..."
	@mkdir -p $(DATA_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/init_database.py

.PHONY: reset-db
reset-db:
	@echo "重置数据库..."
	$(PYTHON) $(SCRIPTS_DIR)/init_database.py --force

.PHONY: verify-db
verify-db:
	@echo "验证数据库..."
	$(PYTHON) $(SCRIPTS_DIR)/init_database.py --verify-only

# 服务管理
.PHONY: start
start:
	@echo "启动所有服务..."
	@mkdir -p $(LOGS_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py start

.PHONY: stop
stop:
	@echo "停止所有服务..."
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py stop

.PHONY: restart
restart:
	@echo "重启所有服务..."
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py restart

.PHONY: status
status:
	@echo "查看服务状态..."
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py status

.PHONY: api
api:
	@echo "启动API服务器..."
	@mkdir -p $(LOGS_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py start --service api

.PHONY: worker
worker:
	@echo "启动工作进程..."
	@mkdir -p $(LOGS_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py start --service worker

.PHONY: balancer
balancer:
	@echo "启动负载均衡器..."
	@mkdir -p $(LOGS_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/start_services.py start --service balancer

# 测试
.PHONY: test
test:
	@echo "运行所有测试..."
	$(PYTEST) $(TEST_DIR) -v

.PHONY: test-unit
test-unit:
	@echo "运行单元测试..."
	$(PYTEST) $(TEST_DIR) -v -m "unit"

.PHONY: test-integration
test-integration:
	@echo "运行集成测试..."
	$(PYTEST) $(TEST_DIR) -v -m "integration"

.PHONY: test-cov
test-cov:
	@echo "运行测试并生成覆盖率报告..."
	$(PYTEST) $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing

.PHONY: test-watch
test-watch:
	@echo "监视文件变化并运行测试..."
	$(PYTEST) $(TEST_DIR) -f

# 代码质量
.PHONY: lint
lint: format type-check security
	@echo "代码质量检查完成"

.PHONY: format
format:
	@echo "格式化代码..."
	$(BLACK) $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR) --profile black

.PHONY: type-check
type-check:
	@echo "类型检查..."
	$(MYPY) $(SRC_DIR)

.PHONY: security
security:
	@echo "安全检查..."
	@command -v bandit >/dev/null 2>&1 && bandit -r $(SRC_DIR) || echo "bandit未安装，跳过安全检查"
	@command -v safety >/dev/null 2>&1 && safety check || echo "safety未安装，跳过依赖安全检查"

# 文档
.PHONY: docs
docs:
	@echo "生成文档..."
	@command -v sphinx-build >/dev/null 2>&1 && sphinx-build -b html docs docs/_build/html || echo "sphinx未安装，无法生成文档"

.PHONY: docs-serve
docs-serve:
	@echo "启动文档服务器..."
	@cd docs/_build/html && $(PYTHON) -m http.server 8080

# 构建和部署
.PHONY: build
build: clean lint test
	@echo "构建项目..."
	$(PYTHON) setup.py build

.PHONY: package
package: build
	@echo "打包项目..."
	$(PYTHON) setup.py sdist bdist_wheel

.PHONY: docker-build
docker-build:
	@echo "构建Docker镜像..."
	@command -v docker >/dev/null 2>&1 && docker build -t mms:latest . || echo "Docker未安装"

.PHONY: docker-run
docker-run:
	@echo "运行Docker容器..."
	@command -v docker >/dev/null 2>&1 && docker run -p 8000:8000 mms:latest || echo "Docker未安装"

# 配置管理
.PHONY: config
config:
	@if [ ! -f $(CONFIG_FILE) ]; then \
		echo "复制配置文件模板..."; \
		cp $(CONFIG_EXAMPLE) $(CONFIG_FILE); \
		echo "请编辑 $(CONFIG_FILE) 以配置您的环境"; \
	else \
		echo "配置文件已存在: $(CONFIG_FILE)"; \
	fi

# 环境检查
.PHONY: check-env
check-env:
	@echo "检查环境..."
	@$(PYTHON) --version
	@$(PIP) --version
	@echo "Python路径: $$(which $(PYTHON))"
	@echo "项目目录: $$(pwd)"
	@if [ -f $(ENV_FILE) ]; then echo "环境文件存在: $(ENV_FILE)"; else echo "环境文件不存在: $(ENV_FILE)"; fi
	@if [ -f $(CONFIG_FILE) ]; then echo "配置文件存在: $(CONFIG_FILE)"; else echo "配置文件不存在: $(CONFIG_FILE)"; fi

# 日志管理
.PHONY: logs
logs:
	@echo "查看日志..."
	@if [ -d $(LOGS_DIR) ]; then \
		ls -la $(LOGS_DIR); \
	else \
		echo "日志目录不存在: $(LOGS_DIR)"; \
	fi

.PHONY: logs-tail
logs-tail:
	@echo "实时查看日志..."
	@if [ -f $(LOGS_DIR)/mms.log ]; then \
		tail -f $(LOGS_DIR)/mms.log; \
	else \
		echo "日志文件不存在: $(LOGS_DIR)/mms.log"; \
	fi

.PHONY: logs-clean
logs-clean:
	@echo "清理日志文件..."
	@if [ -d $(LOGS_DIR) ]; then \
		find $(LOGS_DIR) -name "*.log" -type f -delete; \
		echo "日志文件已清理"; \
	else \
		echo "日志目录不存在: $(LOGS_DIR)"; \
	fi

# 性能测试
.PHONY: benchmark
benchmark:
	@echo "运行性能测试..."
	$(PYTEST) $(TEST_DIR) -v -m "performance" --benchmark-only

# 快速开始
.PHONY: quickstart
quickstart: setup config init-db
	@echo "快速开始完成！"
	@echo "现在可以运行 'make start' 启动服务"

# 完整安装
.PHONY: install-all
install-all: setup install-dev config init-db
	@echo "完整安装完成！"
	@echo "运行 'make test' 验证安装"
	@echo "运行 'make start' 启动服务"

# 开发模式
.PHONY: dev
dev:
	@echo "启动开发模式..."
	@echo "这将启动API服务器并监视文件变化"
	$(PYTHON) -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

# CI/CD相关
.PHONY: ci
ci: lint test-cov security
	@echo "CI检查完成"

.PHONY: pre-commit
pre-commit:
	@echo "运行pre-commit检查..."
	@command -v pre-commit >/dev/null 2>&1 && pre-commit run --all-files || echo "pre-commit未安装"

# 监控和健康检查
.PHONY: health
health:
	@echo "健康检查..."
	@curl -f http://localhost:8000/health || echo "API服务器未响应"

.PHONY: metrics
metrics:
	@echo "查看指标..."
	@curl -f http://localhost:8000/metrics || echo "指标端点未响应"

# 备份和恢复
.PHONY: backup
backup:
	@echo "备份数据..."
	@mkdir -p backups
	@cp -r $(DATA_DIR) backups/data_$$(date +%Y%m%d_%H%M%S)
	@cp -r $(CONFIG_DIR) backups/config_$$(date +%Y%m%d_%H%M%S)
	@echo "备份完成"

.PHONY: restore
restore:
	@echo "恢复数据需要手动操作"
	@echo "请从 backups/ 目录中选择要恢复的备份"
	@ls -la backups/ 2>/dev/null || echo "没有找到备份文件"