#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Factory Module
缁熶竴API绠＄悊宸ュ巶 - NeuroTrade Nexus (NTN) 鏍稿績妯″潡

鏍稿績鍔熻兘锛?
- API缃戝叧鏈嶅姟
- 璁よ瘉涓庢巿鏉?
- 闄愭祦涓庣啍鏂?
- 闆嗙兢绠＄悊

鎶€鏈爤锛?
- FastAPI + Uvicorn
- SQLite + SQLAlchemy
- Redis + aioredis
- ZeroMQ + pyzmq
- JWT + Passlib
"""

__version__ = "1.0.0"
__author__ = "NTN Development Team"
__email__ = "dev@neurotrade-nexus.com"

# 瀵煎嚭鏍稿績缁勪欢
from .main import app
from .config.settings import get_settings

__all__ = [
    "app",
    "get_settings",
]
