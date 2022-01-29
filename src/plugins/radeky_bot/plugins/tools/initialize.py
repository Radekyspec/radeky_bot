from ...utils import initialize
from nonebot import get_driver
from nonebot import logger

__plugin_name__ = 'init'
__plugin_usage__ = """
用法：.init

初始化配置文件。
"""
driver = get_driver()


@driver.on_startup
async def check_initial():
    results = await initialize.check_initial()
    for result in results:
        logger.info(result)
