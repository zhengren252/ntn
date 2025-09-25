@echo off
echo ========================================
echo AI智能体驱动交易系统 V3.5 系统启动脚本
echo ========================================
echo.

echo [1/4] 检查Docker环境...
docker --version
if %errorlevel% neq 0 (
    echo 错误: Docker未安装或未启动
    pause
    exit /b 1
)

echo [2/4] 检查docker-compose.system.yml文件...
if not exist "docker-compose.system.yml" (
    echo 错误: docker-compose.system.yml文件不存在
    pause
    exit /b 1
)

echo [3/4] 停止现有服务...
docker-compose -f docker-compose.system.yml down

echo [4/4] 启动完整系统 (12个模组)...
echo 注意: 首次启动可能需要较长时间进行镜像构建
echo.
docker-compose -f docker-compose.system.yml up --build

echo.
echo 系统启动完成!
echo 访问地址:
echo - Web UI: http://localhost:3000
echo - API Factory: http://localhost:8001
echo - Scanner: http://localhost:8003
echo - Monitor: http://localhost:9090