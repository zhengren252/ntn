@echo off
setlocal enabledelayedexpansion

echo === TACoreService 部署脚本 ===

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker未安装，请先安装Docker Desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker Compose未安装，请先安装Docker Compose
    pause
    exit /b 1
)

REM 创建必要的目录
echo 创建必要的目录...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "config" mkdir config

REM 停止现有服务
echo 停止现有服务...
docker-compose down

REM 构建镜像
echo 构建Docker镜像...
docker-compose build
if errorlevel 1 (
    echo 错误: Docker镜像构建失败
    pause
    exit /b 1
)

REM 启动服务
echo 启动服务...
docker-compose up -d
if errorlevel 1 (
    echo 错误: 服务启动失败
    pause
    exit /b 1
)

REM 等待服务启动
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
docker-compose ps

REM 检查健康状态
echo 检查健康状态...
set /a counter=0
:healthcheck
set /a counter+=1
curl -f http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    if !counter! lss 30 (
        echo 等待服务启动... (!counter!/30)
        timeout /t 2 /nobreak >nul
        goto healthcheck
    ) else (
        echo ❌ 服务启动超时，请检查日志:
        echo docker-compose logs tacoreservice
        pause
        exit /b 1
    )
)

echo ✅ TACoreService启动成功！
echo 监控面板: http://localhost:8000
echo ZeroMQ端口: 5555
echo === 部署完成 ===
pause