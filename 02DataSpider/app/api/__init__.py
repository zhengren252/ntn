# -*- coding: utf-8 -*-
"""
API模块初始化

提供Flask API接口，包含监控面板和配置管理功能
"""

from .app import create_app
from .routes import api_bp
from .middleware import setup_middleware
from .auth import auth_bp
from .monitoring import monitoring_bp
from .config import config_bp

__all__ = [
    "create_app",
    "api_bp",
    "auth_bp",
    "monitoring_bp",
    "config_bp",
    "setup_middleware",
]
