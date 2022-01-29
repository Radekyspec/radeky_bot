from ...utils import refresh
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.params import State
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'refresh'
__plugin_usage__ = r"""
用法：.refresh

刷新uid对应的主播名称
距离上一次刷新7天后机器人会自动刷新
"""


rf = on_command("refresh", permission=SUPERUSER, priority=5)


@rf.handle()
async def refresh_name(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    refresh_done = await refresh.refresh_name()
    await rf.finish(refresh_done)
