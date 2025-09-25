# TACoreService Makefile
# 简化常用开发和部署操作

.PHONY: help install dev test clean build docker run stop logs status

# 默认目标
help:
	@echo "TACoreService 可用命令:"
	@echo ""
	@echo "开发相关:"
	@echo "  install     - 安装依赖"
	@echo "  dev         - 启动开发模式"
	@echo "  test        - 运行测试"
	@echo "  test-cov    - 运行测试并生成覆盖率报告"
	@echo "  lint        - 代码检查"
	@echo "  format      - 代码格式化"
	@echo "  clean       - 清理临时文件"
	@echo ""
	@echo "构建和部署:"
	@echo "  build       - 构建Docker镜像"
	@echo "  docker      - 使用Docker Compose启动"
	@echo "  docker-dev  - 使用Docker Compose启动开发环境"
	@echo "  docker-prod - 使用Docker Compose启动生产环境"
	@echo ""
	@echo "运行和管理:"
	@echo "  run         - 启动服务"
	@echo "  run-prod    - 启动生产模式"
	@echo "  run-workers - 仅启动工作进程"
	@echo "  stop        - 停止服务"
	@echo "  restart     - 重启服务"
	@echo "  status      - 查看服务状态"
	@echo "  logs        - 查看日志"
	@echo ""
	@echo "测试和验证:"
	@echo "  test-health - 健康检查测试"
	@echo "  test-perf   - 性能测试"
	@echo "  test-all    - 完整功能测试"
	@echo ""
	@echo "维护:"
	@echo "  backup      - 备份数据"
	@echo "  restore     - 恢复数据"
	@echo "  cleanup     - 清理旧数据"

# 开发环境设置
install:
	@echo "安装Python依赖..."
	pip install -r requirements.txt
	@echo "创建必要目录..."
	mkdir -p data logs
	@echo "复制配置文件..."
	cp .env.example .env
	@echo "安装完成!"

dev:
	@echo "启动开发模式..."
	python scripts/start.py dev

# 测试
test:
	@echo "运行单元测试..."
	pytest tests/ -v

test-cov:
	@echo "运行测试并生成覆盖率报告..."
	pytest tests/ --cov=tacoreservice --cov-report=html --cov-report=term

test-unit:
	@echo "运行单元测试..."
	pytest tests/ -m unit -v

test-integration:
	@echo "运行集成测试..."
	pytest tests/ -m integration -v

test-health:
	@echo "运行健康检查测试..."
	python scripts/test.py health

test-perf:
	@echo "运行性能测试..."
	python scripts/test.py performance --iterations 1000

test-all:
	@echo "运行完整功能测试..."
	python scripts/test.py all

# 代码质量
lint:
	@echo "运行代码检查..."
	flake8 tacoreservice/ tests/
	mypy tacoreservice/

format:
	@echo "格式化代码..."
	black tacoreservice/ tests/ scripts/
	isort tacoreservice/ tests/ scripts/

# 清理
clean:
	@echo "清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	@echo "清理完成!"

# Docker相关
build:
	@echo "构建Docker镜像..."
	docker build -t tacoreservice:latest .

docker:
	@echo "启动Docker Compose..."
	docker-compose up -d

docker-dev:
	@echo "启动Docker开发环境..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

docker-prod:
	@echo "启动Docker生产环境..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

docker-stop:
	@echo "停止Docker服务..."
	docker-compose down

docker-logs:
	@echo "查看Docker日志..."
	docker-compose logs -f

docker-clean:
	@echo "清理Docker资源..."
	docker-compose down -v
	docker system prune -f

# 服务管理
run:
	@echo "启动TACoreService..."
	python scripts/start.py dev

run-prod:
	@echo "启动生产模式..."
	python scripts/start.py prod

run-workers:
	@echo "启动工作进程..."
	python scripts/start.py workers --workers 4

run-monitoring:
	@echo "启动监控API..."
	python scripts/start.py monitoring

stop:
	@echo "停止TACoreService..."
	python scripts/stop.py stop

stop-force:
	@echo "强制停止TACoreService..."
	python scripts/stop.py kill

restart: stop
	@echo "等待服务停止..."
	sleep 3
	@echo "重新启动服务..."
	make run

status:
	@echo "查看服务状态..."
	python scripts/stop.py list

logs:
	@echo "查看服务日志..."
	tail -f logs/tacoreservice.log

logs-error:
	@echo "查看错误日志..."
	tail -f logs/tacoreservice_errors.log

logs-requests:
	@echo "查看请求日志..."
	tail -f logs/tacoreservice_requests.log

# 数据库管理
db-init:
	@echo "初始化数据库..."
	python -c "from tacoreservice.core.database import DatabaseManager; from tacoreservice.config import get_settings; db = DatabaseManager(get_settings()); db.initialize()"

db-backup:
	@echo "备份数据库..."
	mkdir -p data/backups
	cp data/tacoreservice.db data/backups/tacoreservice_$(shell date +%Y%m%d_%H%M%S).db

db-restore:
	@echo "恢复数据库 (需要指定备份文件)..."
	@echo "使用: cp data/backups/backup_file.db data/tacoreservice.db"

db-clean:
	@echo "清理旧数据..."
	python -c "from tacoreservice.core.database import DatabaseManager; from tacoreservice.config import get_settings; db = DatabaseManager(get_settings()); db.cleanup_old_data(days=30)"

# 监控和指标
metrics:
	@echo "查看服务指标..."
	curl -s http://localhost:8080/metrics

health:
	@echo "检查服务健康状态..."
	curl -s http://localhost:8080/health | python -m json.tool

api-status:
	@echo "查看API状态..."
	curl -s http://localhost:8080/api/status | python -m json.tool

workers-status:
	@echo "查看工作进程状态..."
	curl -s http://localhost:8080/api/workers | python -m json.tool

# 性能分析
profile:
	@echo "运行性能分析..."
	python -m cProfile -o profile.stats main.py
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

benchmark:
	@echo "运行基准测试..."
	python scripts/test.py performance --iterations 10000

# 部署相关
deploy-staging:
	@echo "部署到测试环境..."
	# 添加具体的部署命令

deploy-prod:
	@echo "部署到生产环境..."
	# 添加具体的部署命令

# 文档生成
docs:
	@echo "生成文档..."
	# 如果使用Sphinx或其他文档工具
	# sphinx-build -b html docs/ docs/_build/

# 安全检查
security:
	@echo "运行安全检查..."
	bandit -r tacoreservice/
	safety check

# 依赖管理
update-deps:
	@echo "更新依赖..."
	pip list --outdated
	@echo "请手动更新requirements.txt中的版本"

check-deps:
	@echo "检查依赖漏洞..."
	safety check
	pip-audit

# 环境检查
check-env:
	@echo "检查环境配置..."
	python -c "from tacoreservice.config import get_settings; settings = get_settings(); print(f'Service: {settings.service_name}'); print(f'Debug: {settings.debug}'); print(f'ZMQ Port: {settings.zmq_frontend_port}'); print(f'HTTP Port: {settings.http_port}')"

# 快速启动（开发用）
quick-start: install
	@echo "快速启动开发环境..."
	make dev

# 完整测试流程
full-test: clean test-cov lint
	@echo "完整测试流程完成!"

# 发布准备
release-prep: clean full-test build
	@echo "发布准备完成!"

# 帮助信息
info:
	@echo "TACoreService 项目信息:"
	@echo "  项目名称: TACoreService"
	@echo "  版本: 1.0.0"
	@echo "  Python版本: $(shell python --version)"
	@echo "  当前目录: $(shell pwd)"
	@echo "  配置文件: .env"
	@echo "  数据目录: data/"
	@echo "  日志目录: logs/"