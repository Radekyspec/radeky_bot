from ...utils import initialize
from nonebot import get_driver
from nonebot.adapters.cqhttp import Bot

__plugin_name__ = 'init'
__plugin_usage__ = """
用法：.init

初始化配置文件。
"""
driver = get_driver()


@driver.on_bot_connect
async def check_initial(bot: Bot):
    superuser = "".join(bot.config.superusers)
    results = await initialize.check_initial()
    for result in results:
        await bot.call_api(api="send_private_msg", **{"user_id": superuser, "message": result})
