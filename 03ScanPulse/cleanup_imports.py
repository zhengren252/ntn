#!/usr/bin/env python3
"""
清理未使用的导入脚本
"""

import re
import os
from pathlib import Path

# 需要清理的未使用导入映射
CLEANUP_MAP = {
    "scanner/communication/communication_manager.py": [
        "from .message_formatter import StandardMessage",
        "from .zmq_client import ScannerZMQClient",
    ],
    "scanner/communication/message_formatter.py": [
        "from typing import Any, Dict, List, Optional, Union"
    ],
    "scanner/communication/redis_client.py": [
        "import asyncio",
        "import pickle",
        "from typing import Any, Dict, List, Optional, Union",
    ],
    "scanner/core/data_processor.py": ["import numpy as np"],
    "scanner/core/result_aggregator.py": [
        "from typing import Any, Dict, List, Optional, Tuple"
    ],
    "scanner/core/scanner_controller.py": [
        "from typing import Any, Dict, List, Optional"
    ],
    "scanner/rules/black_horse.py": ["import re"],
    "scanner/rules/engine.py": ["from abc import ABC, abstractmethod"],
    "scanner/rules/potential_finder.py": [
        "from datetime import datetime, timedelta",
        "from typing import Any, Dict, List, Optional",
    ],
    "scanner/storage/redis_client.py": [
        "from datetime import datetime, timedelta",
        "from typing import Any, Dict, List, Optional, Union",
    ],
    "scanner/utils/enhanced_logger.py": [
        "import asyncio",
        "import functools",
        "import inspect",
        "import json",
        "import os",
        "import time",
        "from contextlib import contextmanager",
    ],
    "scanner/web/app.py": [
        "from flask import Flask, render_template, jsonify, request, send_from_directory"
    ],
}

# 替换映射 - 将复杂的导入替换为简化版本
REPLACE_MAP = {
    "scanner/communication/message_formatter.py": {
        "from typing import Any, Dict, List, Optional, Union": "from typing import Any, Dict, List, Optional"
    },
    "scanner/communication/redis_client.py": {
        "from typing import Any, Dict, List, Optional, Union": "from typing import Any, Dict, List, Optional"
    },
    "scanner/core/result_aggregator.py": {
        "from typing import Any, Dict, List, Optional, Tuple": "from typing import Any, Dict, List, Optional"
    },
    "scanner/core/scanner_controller.py": {
        "from typing import Any, Dict, List, Optional": "from typing import Any, Dict, Optional"
    },
    "scanner/rules/potential_finder.py": {
        "from datetime import datetime, timedelta": "from datetime import datetime",
        "from typing import Any, Dict, List, Optional": "from typing import Any, Dict, List",
    },
    "scanner/storage/redis_client.py": {
        "from datetime import datetime, timedelta": "from datetime import datetime",
        "from typing import Any, Dict, List, Optional, Union": "from typing import Any, Dict, List, Optional",
    },
    "scanner/rules/engine.py": {
        "from abc import ABC, abstractmethod": "# from abc import ABC, abstractmethod  # Unused"
    },
    "scanner/web/app.py": {
        "from flask import Flask, render_template, jsonify, request, send_from_directory": "from flask import Flask, render_template, jsonify, request"
    },
}


def cleanup_file(file_path: str):
    """清理单个文件的未使用导入"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 应用替换映射
    if file_path in REPLACE_MAP:
        for old_import, new_import in REPLACE_MAP[file_path].items():
            content = content.replace(old_import, new_import)

    # 删除完全未使用的导入
    if file_path in CLEANUP_MAP:
        for unused_import in CLEANUP_MAP[file_path]:
            # 删除整行
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if unused_import.strip() not in line.strip():
                    new_lines.append(line)
            content = "\n".join(new_lines)

    # 如果内容有变化，写回文件
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"已清理: {file_path}")
    else:
        print(f"无需清理: {file_path}")


def main():
    """主函数"""
    print("开始清理未使用的导入...")

    # 清理所有映射中的文件
    all_files = set(list(CLEANUP_MAP.keys()) + list(REPLACE_MAP.keys()))

    for file_path in all_files:
        cleanup_file(file_path)

    print("清理完成！")


if __name__ == "__main__":
    main()
