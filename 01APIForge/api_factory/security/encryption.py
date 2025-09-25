#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Factory Module - 加密工具
实现AES-256-GCM加密算法用于API密钥安全存储
"""

import os
import base64
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """加密管理器 - AES-256-GCM实现"""

    def __init__(self, encryption_key: str):
        """
        初始化加密管理器
        
        Args:
            encryption_key: 32字节的加密密钥（Base64编码）
        """
        try:
            # 解码Base64密钥
            self.key = base64.b64decode(encryption_key)
            if len(self.key) != 32:
                raise ValueError("加密密钥必须是32字节")
            
            self.aesgcm = AESGCM(self.key)
            logger.info("加密管理器初始化成功")
        except Exception as e:
            logger.error(f"加密管理器初始化失败: {e}")
            raise

    def encrypt(self, plaintext: str, associated_data: Optional[str] = None) -> str:
        """
        加密明文
        
        Args:
            plaintext: 要加密的明文
            associated_data: 关联数据（可选）
            
        Returns:
            Base64编码的加密数据（包含nonce）
        """
        try:
            # 生成随机nonce（12字节）
            nonce = os.urandom(12)
            
            # 准备关联数据
            aad = associated_data.encode('utf-8') if associated_data else None
            
            # 加密
            ciphertext = self.aesgcm.encrypt(
                nonce, 
                plaintext.encode('utf-8'), 
                aad
            )
            
            # 组合nonce和密文
            encrypted_data = nonce + ciphertext
            
            # Base64编码
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise

    def decrypt(self, encrypted_data: str, associated_data: Optional[str] = None) -> str:
        """
        解密密文
        
        Args:
            encrypted_data: Base64编码的加密数据
            associated_data: 关联数据（可选）
            
        Returns:
            解密后的明文
        """
        try:
            # Base64解码
            data = base64.b64decode(encrypted_data)
            
            # 分离nonce和密文
            nonce = data[:12]
            ciphertext = data[12:]
            
            # 准备关联数据
            aad = associated_data.encode('utf-8') if associated_data else None
            
            # 解密
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, aad)
            
            return plaintext.decode('utf-8')
            
        except InvalidTag:
            logger.error("解密失败: 无效的认证标签")
            raise ValueError("解密失败: 数据可能被篡改")
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise

    def generate_key(self) -> str:
        """
        生成新的32字节加密密钥
        
        Returns:
            Base64编码的密钥
        """
        key = os.urandom(32)
        return base64.b64encode(key).decode('utf-8')

    def mask_key(self, api_key: str, visible_chars: int = 4) -> str:
        """
        遮盖API密钥，只显示前几位和后几位
        
        Args:
            api_key: 原始API密钥
            visible_chars: 可见字符数
            
        Returns:
            遮盖后的密钥
        """
        if len(api_key) <= visible_chars * 2:
            return '*' * len(api_key)
        
        prefix = api_key[:visible_chars]
        suffix = api_key[-visible_chars:]
        middle = '*' * (len(api_key) - visible_chars * 2)
        
        return f"{prefix}{middle}{suffix}"


def create_encryption_manager(encryption_key: str) -> EncryptionManager:
    """
    创建加密管理器实例
    
    Args:
        encryption_key: 加密密钥
        
    Returns:
        EncryptionManager实例
    """
    return EncryptionManager(encryption_key)


# 密钥生成工具函数
def generate_encryption_key() -> str:
    """
    生成新的加密密钥
    
    Returns:
        Base64编码的32字节密钥
    """
    key = os.urandom(32)
    return base64.b64encode(key).decode('utf-8')


if __name__ == "__main__":
    # 测试代码
    print("生成新的加密密钥:")
    test_key = generate_encryption_key()
    print(f"密钥: {test_key}")
    
    # 测试加密解密
    manager = EncryptionManager(test_key)
    
    test_data = "sk-1234567890abcdef"
    print(f"\n原始数据: {test_data}")
    
    encrypted = manager.encrypt(test_data, "api_key")
    print(f"加密数据: {encrypted}")
    
    decrypted = manager.decrypt(encrypted, "api_key")
    print(f"解密数据: {decrypted}")
    
    masked = manager.mask_key(test_data)
    print(f"遮盖数据: {masked}")