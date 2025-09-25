#!/bin/bash

# ReviewGuard部署脚本

set -e

echo "🚀 ReviewGuard部署脚本"
echo "========================"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 解析命令行参数
ENV=${1:-production}
ACTION=${2:-up}

echo "📋 环境: $ENV"
echo "📋 操作: $ACTION"
echo ""

# 选择配置文件
if [ "$ENV" = "development" ] || [ "$ENV" = "dev" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    ENV_FILE=".env.example"
else
    COMPOSE_FILE="docker-compose.yml"
    ENV_FILE=".env.production"
fi

echo "📁 使用配置文件: $COMPOSE_FILE"
echo "📁 使用环境文件: $ENV_FILE"
echo ""

# 检查环境文件
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  环境文件 $ENV_FILE 不存在，使用默认配置"
fi

# 执行操作
case $ACTION in
    "up")
        echo "🔄 启动服务..."
        docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
        echo "✅ 服务启动完成"
        echo ""
        echo "📊 服务状态:"
        docker-compose -f $COMPOSE_FILE ps
        echo ""
        if [ "$ENV" = "development" ] || [ "$ENV" = "dev" ]; then
            echo "🌐 前端地址: http://localhost:3000"
            echo "🔧 后端API: http://localhost:8000"
            echo "📚 API文档: http://localhost:8000/docs"
        else
            echo "🔧 后端API: http://localhost:8000"
            echo "📚 API文档: http://localhost:8000/docs"
        fi
        ;;
    "down")
        echo "🛑 停止服务..."
        docker-compose -f $COMPOSE_FILE down
        echo "✅ 服务停止完成"
        ;;
    "restart")
        echo "🔄 重启服务..."
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
        echo "✅ 服务重启完成"
        ;;
    "build")
        echo "🔨 构建镜像..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        echo "✅ 镜像构建完成"
        ;;
    "logs")
        echo "📋 查看日志..."
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    "status")
        echo "📊 服务状态:"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    "clean")
        echo "🧹 清理资源..."
        docker-compose -f $COMPOSE_FILE down -v
        docker system prune -f
        echo "✅ 清理完成"
        ;;
    *)
        echo "❌ 未知操作: $ACTION"
        echo ""
        echo "用法: $0 [environment] [action]"
        echo ""
        echo "环境:"
        echo "  production (默认) - 生产环境"
        echo "  development/dev   - 开发环境"
        echo ""
        echo "操作:"
        echo "  up (默认)  - 启动服务"
        echo "  down       - 停止服务"
        echo "  restart    - 重启服务"
        echo "  build      - 构建镜像"
        echo "  logs       - 查看日志"
        echo "  status     - 查看状态"
        echo "  clean      - 清理资源"
        echo ""
        echo "示例:"
        echo "  $0                    # 生产环境启动"
        echo "  $0 dev up            # 开发环境启动"
        echo "  $0 production down   # 生产环境停止"
        exit 1
        ;;
esac

echo ""
echo "🎉 操作完成！"