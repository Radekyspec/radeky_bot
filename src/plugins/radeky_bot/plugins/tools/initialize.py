from . import ws_monitor
from ...utils import initialize
from nonebot import get_driver
from nonebot import logger

driver = get_driver()


@driver.on_startup
async def check_initial():
    logger.info("正在建立与弹幕服务器的连接...")
    await ws_monitor.start_ws()
    results = await initialize.check_initial()
    for result in results:
        logger.success(result)


@driver.on_shutdown
async def shutdown():
    await ws_monitor.stop_ws()
    logger.info("正在关闭与弹幕服务器的连接...")
