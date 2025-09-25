@echo off
REM 扫描器模组Docker部署脚本 - Windows版本
REM 支持多环境部署和服务管理

setlocal enabledelayedexpansion

REM 设置变量
set "ENVIRONMENT=dev"
set "COMMAND="
set "VERBOSE=false"
set "FORCE=false"
set "NO_CACHE=false"
set "PULL=false"

REM 颜色定义（Windows CMD限制）
set "INFO_COLOR=[94m"
set "SUCCESS_COLOR=[92m"
set "WARNING_COLOR=[93m"
set "ERROR_COLOR=[91m"
set "RESET_COLOR=[0m"

REM 日志函数
:log_info
echo %INFO_COLOR%[INFO]%RESET_COLOR% %~1
goto :eof

:log_success
echo %SUCCESS_COLOR%[SUCCESS]%RESET_COLOR% %~1
goto :eof

:log_warning
echo %WARNING_COLOR%[WARNING]%RESET_COLOR% %~1
goto :eof

:log_error
echo %ERROR_COLOR%[ERROR]%RESET_COLOR% %~1
goto :eof

REM 显示帮助信息
:show_help
echo 扫描器模组Docker部署脚本 - Windows版本
echo.
echo 用法: %~nx0 [选项] ^<命令^> [环境]
echo.
echo 命令:
echo   start     启动服务
echo   stop      停止服务
echo   restart   重启服务
echo   build     构建镜像
echo   logs      查看日志
echo   status    查看状态
echo   clean     清理资源
echo   health    健康检查
echo.
echo 环境:
echo   dev       开发环境 (默认)
echo   prod      生产环境
echo.
echo 选项:
echo   /h, /help     显示帮助信息
echo   /v, /verbose  详细输出
echo   /f, /force    强制执行
echo   /no-cache     构建时不使用缓存
echo   /pull         构建前拉取最新基础镜像
echo.
echo 示例:
echo   %~nx0 start dev              启动开发环境
echo   %~nx0 build prod /no-cache   无缓存构建生产环境
echo   %~nx0 logs dev               查看开发环境日志
echo   %~nx0 health prod            生产环境健康检查
goto :eof

REM 解析参数
:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="/h" goto :show_help_and_exit
if /i "%~1"=="/help" goto :show_help_and_exit
if /i "%~1"=="/v" set "VERBOSE=true" & shift & goto :parse_args
if /i "%~1"=="/verbose" set "VERBOSE=true" & shift & goto :parse_args
if /i "%~1"=="/f" set "FORCE=true" & shift & goto :parse_args
if /i "%~1"=="/force" set "FORCE=true" & shift & goto :parse_args
if /i "%~1"=="/no-cache" set "NO_CACHE=true" & shift & goto :parse_args
if /i "%~1"=="/pull" set "PULL=true" & shift & goto :parse_args
if /i "%~1"=="start" set "COMMAND=start" & shift & goto :parse_args
if /i "%~1"=="stop" set "COMMAND=stop" & shift & goto :parse_args
if /i "%~1"=="restart" set "COMMAND=restart" & shift & goto :parse_args
if /i "%~1"=="build" set "COMMAND=build" & shift & goto :parse_args
if /i "%~1"=="logs" set "COMMAND=logs" & shift & goto :parse_args
if /i "%~1"=="status" set "COMMAND=status" & shift & goto :parse_args
if /i "%~1"=="clean" set "COMMAND=clean" & shift & goto :parse_args
if /i "%~1"=="health" set "COMMAND=health" & shift & goto :parse_args
if /i "%~1"=="dev" set "ENVIRONMENT=dev" & shift & goto :parse_args
if /i "%~1"=="prod" set "ENVIRONMENT=prod" & shift & goto :parse_args
call :log_error "未知参数: %~1"
call :show_help
exit /b 1

:show_help_and_exit
call :show_help
exit /b 0

:args_done
REM 检查命令
if "%COMMAND%"=="" (
    call :log_error "请指定命令"
    call :show_help
    exit /b 1
)

REM 设置环境变量
if "%ENVIRONMENT%"=="dev" (
    set "COMPOSE_FILE=docker-compose.dev.yml"
    set "PROJECT_NAME=scanner-dev"
) else (
    set "COMPOSE_FILE=docker-compose.yml"
    set "PROJECT_NAME=scanner-prod"
)

REM 检查依赖
:check_dependencies
call :log_info "检查依赖..."

docker --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Docker未安装或不在PATH中"
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Docker Compose未安装或不在PATH中"
    exit /b 1
)

call :log_success "依赖检查通过"
goto :eof

REM 构建镜像
:build_images
call :log_info "构建%ENVIRONMENT%环境镜像..."

set "BUILD_ARGS="
if "%NO_CACHE%"=="true" set "BUILD_ARGS=%BUILD_ARGS% --no-cache"
if "%PULL%"=="true" set "BUILD_ARGS=%BUILD_ARGS% --pull"

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" build %BUILD_ARGS%
if errorlevel 1 (
    call :log_error "镜像构建失败"
    exit /b 1
)

call :log_success "镜像构建完成"
goto :eof

REM 启动服务
:start_services
call :log_info "启动%ENVIRONMENT%环境服务..."

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" up -d
if errorlevel 1 (
    call :log_error "服务启动失败"
    exit /b 1
)

call :log_success "服务启动完成"

REM 等待服务就绪
call :log_info "等待服务就绪..."
timeout /t 10 /nobreak >nul

REM 显示服务状态
docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps
goto :eof

REM 停止服务
:stop_services
call :log_info "停止%ENVIRONMENT%环境服务..."

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" down
if errorlevel 1 (
    call :log_error "服务停止失败"
    exit /b 1
)

call :log_success "服务停止完成"
goto :eof

REM 重启服务
:restart_services
call :log_info "重启%ENVIRONMENT%环境服务..."

call :stop_services
if errorlevel 1 exit /b 1

call :start_services
if errorlevel 1 exit /b 1

call :log_success "服务重启完成"
goto :eof

REM 查看日志
:show_logs
call :log_info "显示%ENVIRONMENT%环境日志..."

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" logs -f
goto :eof

REM 查看状态
:show_status
call :log_info "%ENVIRONMENT%环境服务状态:"

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps

echo.
call :log_info "容器资源使用情况:"
for /f "tokens=*" %%i in ('docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps -q') do (
    docker stats --no-stream %%i
)
goto :eof

REM 清理资源
:clean_resources
call :log_warning "清理%ENVIRONMENT%环境资源..."

if "%FORCE%"=="false" (
    set /p "REPLY=确定要清理所有资源吗？这将删除容器、网络和卷 [y/N]: "
    if /i not "!REPLY!"=="y" (
        call :log_info "取消清理操作"
        exit /b 0
    )
)

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" down -v --remove-orphans
docker system prune -f

call :log_success "资源清理完成"
goto :eof

REM 健康检查
:health_check
call :log_info "执行%ENVIRONMENT%环境健康检查..."

REM 检查容器状态
for /f "tokens=*" %%i in ('docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps -q 2^>nul') do (
    set "CONTAINERS=%%i"
)

if "%CONTAINERS%"=="" (
    call :log_error "没有运行的容器"
    exit /b 1
)

set "ALL_HEALTHY=true"

for /f "tokens=*" %%i in ('docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps -q') do (
    for /f "tokens=*" %%j in ('docker inspect --format="{{.State.Health.Status}}" %%i 2^>nul') do (
        set "HEALTH=%%j"
    )
    for /f "tokens=*" %%k in ('docker inspect --format="{{.Name}}" %%i') do (
        set "NAME=%%k"
        set "NAME=!NAME:~1!"
    )
    
    if "!HEALTH!"=="healthy" (
        call :log_success "!NAME!: 健康"
    ) else if "!HEALTH!"=="" (
        call :log_success "!NAME!: 健康 (无健康检查)"
    ) else (
        call :log_error "!NAME!: 不健康 (!HEALTH!)"
        set "ALL_HEALTHY=false"
    )
)

if "%ALL_HEALTHY%"=="true" (
    call :log_success "所有服务健康"
    exit /b 0
) else (
    call :log_error "部分服务不健康"
    exit /b 1
)

REM 主逻辑
:main
call :parse_args %*
call :check_dependencies

if "%COMMAND%"=="build" call :build_images
if "%COMMAND%"=="start" call :start_services
if "%COMMAND%"=="stop" call :stop_services
if "%COMMAND%"=="restart" call :restart_services
if "%COMMAND%"=="logs" call :show_logs
if "%COMMAND%"=="status" call :show_status
if "%COMMAND%"=="clean" call :clean_resources
if "%COMMAND%"=="health" call :health_check

if errorlevel 1 exit /b 1
exit /b 0

REM 执行主函数
call :main %*