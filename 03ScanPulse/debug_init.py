#!/usr/bin/env python3
# Debug script to test component initialization step by step

import asyncio
import sys
from pathlib import Path

# Add scanner module to path
sys.path.insert(0, str(Path(__file__).parent / "scanner"))

from scanner.config.env_manager import get_env_manager
from scanner.utils.logger import setup_logging, get_logger, get_error_handler
from scanner.communication.redis_client import RedisClient
from scanner.communication.zmq_client import ScannerZMQClient
from scanner.health_check import get_health_checker

async def test_initialization():
    """Test each component initialization step by step"""
    print("=== Starting Component Initialization Test ===")
    
    try:
        # Step 1: Environment Manager
        print("\n1. Testing Environment Manager...")
        env_manager = get_env_manager()
        print("✓ Environment Manager initialized")
        
        # Step 2: Logging System
        print("\n2. Testing Logging System...")
        logging_config = env_manager.get_logging_config()
        setup_logging(logging_config)
        logger = get_logger(__name__)
        error_handler = get_error_handler()
        print("✓ Logging System initialized")
        
        # Step 3: Redis Client
        print("\n3. Testing Redis Client...")
        redis_config = env_manager.get_redis_config()
        print(f"Redis config: {redis_config}")
        redis_client = RedisClient(redis_config)
        print("✓ Redis Client created")
        
        # Test Redis connection
        print("Testing Redis connection...")
        if redis_client.ping():
            print("✓ Redis connection successful")
        else:
            print("✗ Redis connection failed")
            
        # Step 4: ZMQ Client
        print("\n4. Testing ZMQ Client...")
        zmq_config = env_manager.get_zmq_config()
        print(f"ZMQ config: {zmq_config}")
        zmq_client = ScannerZMQClient(zmq_config)
        print("✓ ZMQ Client created")
        
        # Step 5: Health Checker
        print("\n5. Testing Health Checker...")
        health_checker = get_health_checker()
        print("✓ Health Checker initialized")
        
        # Step 6: Configuration Validation
        print("\n6. Testing Configuration Validation...")
        validation_result = env_manager.validate_config()
        print(f"Validation result: {validation_result}")
        
        if validation_result["valid"]:
            print("✓ Configuration validation passed")
        else:
            print("✗ Configuration validation failed")
            print(f"Errors: {validation_result['errors']}")
            
        if validation_result.get("warnings"):
            print(f"Warnings: {validation_result['warnings']}")
            
        print("\n=== All Components Initialized Successfully ===")
        return True
        
    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_initialization())
    sys.exit(0 if success else 1)