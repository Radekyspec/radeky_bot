from nonebot import logger
from nonebot.adapters import Bot
from nonebot.exception import ActionFailed, NetworkError


async def call_api(bot: Bot, api: str, kwargs: dict, errors: int = 0):
    if errors < 5:
        try:
            await bot.call_api(api=api, **kwargs)
        except (ActionFailed, NetworkError):
            errors += 1
            await call_api(bot, api, kwargs, errors)
    else:
        logger.error("消息发送失败, 账号可能被风控.")
