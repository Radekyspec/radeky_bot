from typing import Optional
from pydantic import BaseSettings


# 其他地方出现的类似 from .. import config，均是从 __init__.py 导入的 Config 实例
class Config(BaseSettings):
    radeky_dir: Optional[str] = None

    class Config:
        extra = "ignore"
