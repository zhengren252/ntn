#!/bin/bash

# TACoreService部署脚本

set -e

echo "=== TACoreService 部署脚本 ==="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p data logs config

# 停止现有服务
echo "停止现有服务..."
docker-compose down

# 构建镜像
echo "构建Docker镜像..."
docker-compose build

# 启动服务
echo "启动服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker-compose ps

# 检查健康状态
echo "检查健康状态..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ TACoreService启动成功！"
        echo "监控面板: http://localhost:8000"
        echo "ZeroMQ端口: 5555"
        break
    fi
    echo "等待服务启动... ($i/30)"
    sleep 2
done

if [ $i -eq 30 ]; then
    echo "❌ 服务启动超时，请检查日志:"
    echo "docker-compose logs tacoreservice"
    exit 1
fi

echo "=== 部署完成 ==="