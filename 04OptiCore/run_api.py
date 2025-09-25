import os
import sys

import uvicorn

# 将项目根目录添加到 sys.path
# 这确保了无论从哪里运行脚本，`optimizer`、`config` 等模块都能被找到
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 打印当前的 sys.path 用于调试
print("Current sys.path:", sys.path)

from api.app import app
from config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
