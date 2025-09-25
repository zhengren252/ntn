@echo off
setlocal enabledelayedexpansion

echo 🚀 ReviewGuard部署脚本
echo ========================
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未安装，请先安装Docker
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose未安装，请先安装Docker Compose
    pause
    exit /b 1
)

REM 解析命令行参数
set "ENV=%1"
set "ACTION=%2"

if "%ENV%"=="" set "ENV=production"
if "%ACTION%"=="" set "ACTION=up"

echo 📋 环境: %ENV%
echo 📋 操作: %ACTION%
echo.

REM 选择配置文件
if "%ENV%"=="development" (
    set "COMPOSE_FILE=docker-compose.dev.yml"
    set "ENV_FILE=.env.example"
) else if "%ENV%"=="dev" (
    set "COMPOSE_FILE=docker-compose.dev.yml"
    set "ENV_FILE=.env.example"
) else (
    set "COMPOSE_FILE=docker-compose.yml"
    set "ENV_FILE=.env.production"
)

echo 📁 使用配置文件: %COMPOSE_FILE%
echo 📁 使用环境文件: %ENV_FILE%
echo.

REM 检查环境文件
if not exist "%ENV_FILE%" (
    echo ⚠️  环境文件 %ENV_FILE% 不存在，使用默认配置
)

REM 执行操作
if "%ACTION%"=="up" (
    echo 🔄 启动服务...
    docker-compose -f %COMPOSE_FILE% --env-file %ENV_FILE% up -d
    echo ✅ 服务启动完成
    echo.
    echo 📊 服务状态:
    docker-compose -f %COMPOSE_FILE% ps
    echo.
    if "%ENV%"=="development" (
        echo 🌐 前端地址: http://localhost:3000
        echo 🔧 后端API: http://localhost:8000
        echo 📚 API文档: http://localhost:8000/docs
    ) else if "%ENV%"=="dev" (
        echo 🌐 前端地址: http://localhost:3000
        echo 🔧 后端API: http://localhost:8000
        echo 📚 API文档: http://localhost:8000/docs
    ) else (
        echo 🔧 后端API: http://localhost:8000
        echo 📚 API文档: http://localhost:8000/docs
    )
) else if "%ACTION%"=="down" (
    echo 🛑 停止服务...
    docker-compose -f %COMPOSE_FILE% down
    echo ✅ 服务停止完成
) else if "%ACTION%"=="restart" (
    echo 🔄 重启服务...
    docker-compose -f %COMPOSE_FILE% down
    docker-compose -f %COMPOSE_FILE% --env-file %ENV_FILE% up -d
    echo ✅ 服务重启完成
) else if "%ACTION%"=="build" (
    echo 🔨 构建镜像...
    docker-compose -f %COMPOSE_FILE% build --no-cache
    echo ✅ 镜像构建完成
) else if "%ACTION%"=="logs" (
    echo 📋 查看日志...
    docker-compose -f %COMPOSE_FILE% logs -f
) else if "%ACTION%"=="status" (
    echo 📊 服务状态:
    docker-compose -f %COMPOSE_FILE% ps
) else if "%ACTION%"=="clean" (
    echo 🧹 清理资源...
    docker-compose -f %COMPOSE_FILE% down -v
    docker system prune -f
    echo ✅ 清理完成
) else (
    echo ❌ 未知操作: %ACTION%
    echo.
    echo 用法: %0 [environment] [action]
    echo.
    echo 环境:
    echo   production ^(默认^) - 生产环境
    echo   development/dev   - 开发环境
    echo.
    echo 操作:
    echo   up ^(默认^)  - 启动服务
    echo   down       - 停止服务
    echo   restart    - 重启服务
    echo   build      - 构建镜像
    echo   logs       - 查看日志
    echo   status     - 查看状态
    echo   clean      - 清理资源
    echo.
    echo 示例:
    echo   %0                    # 生产环境启动
    echo   %0 dev up            # 开发环境启动
    echo   %0 production down   # 生产环境停止
    pause
    exit /b 1
)

echo.
echo 🎉 操作完成！
if "%ACTION%"=="up" (
    echo.
    echo 按任意键继续...
    pause >nul
)