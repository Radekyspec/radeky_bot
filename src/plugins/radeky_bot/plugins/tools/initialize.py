from nonebot import get_driver
from nonebot import logger

from .ws_monitor import Monitor
from ...utils import initialize

driver = get_driver()
m = Monitor()


@driver.on_startup
async def check_initial():
    logger.info("正在建立与弹幕服务器的连接...")
    results = await initialize.check_initial()
    await m.start_ws()
    for result in results:
        logger.success(result)


@driver.on_shutdown
async def shutdown():
    await m.stop_ws()
    logger.info("正在关闭与弹幕服务器的连接...")
