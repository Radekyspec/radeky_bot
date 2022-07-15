from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import State, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ...utils.get_user_info import GetUserInfo

announce = on_command("announce", permission=SUPERUSER, priority=5)


@announce.handle()
async def announcer(bot: Bot, event: PrivateMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    msg = str(message).strip()
    if msg:
        state["message"] = msg


@announce.got("message", prompt="请输入公告内容")
async def msg_handler(bot: Bot, event: PrivateMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    msg = str(state["message"])
    if not msg:
        await announce.reject("公告内容不能为空！")
    else:
        await announce_sender(bot, msg)
        await announce.finish()
    return


async def announce_sender(bot: Bot, message: str):
    groups = await GetUserInfo().get_group_list(union=True)
    announcement = "【Announcement】\n\n" + message
    for group in groups:
        await bot.call_api(api="send_group_msg", **{"group_id": group, "message": announcement})
    return
