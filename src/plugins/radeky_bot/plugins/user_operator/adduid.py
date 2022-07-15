from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import State, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ...utils import refresh, read_file, write_file
from ..tools.ws_monitor import Monitor

__plugin_name__ = "add"
__plugin_usage__ = r"""
用法：.add <uid>

把uid对应的主播加入监控列表。
"""

add_uid = on_command("add", permission=SUPERUSER, priority=5)


@add_uid.handle()
async def get_uid(bot: Bot, event: PrivateMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    uid = str(message).strip()
    if uid:
        state["uid"] = uid


@add_uid.got("uid", prompt="请输入需要关注用户的UID：")
async def handle_uid(bot: Bot, event: PrivateMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    uid = str(state["uid"])
    try:
        uid = int(uid)
    except ValueError:
        await add_uid.reject("UID只能为数字！请重新输入！")
    else:
        uid = str(uid)
        user_added = await add_user_uid(uid)
        await add_uid.finish(user_added)


async def add_user_uid(uid: str) -> str:
    setting_dic = read_file.read_settings()
    try:
        user_dic = await read_file.read_users()
    except FileNotFoundError:
        user_dic = {}
    if user_dic is None:
        user_dic = {}

    user_dic[uid] = ""
    setting_dic[uid] = {"group": "", "atall": False, "title": True, "dynamic": True, "live": True, "room_id": 0,
                        "interval": 0}

    write_file.write_settings(setting_dic)
    await write_file.write_users(user_dic)
    await refresh.refresh_name()
    
    user_dic = await read_file.read_users()
    setting_dic = read_file.read_settings()
    Monitor.add(setting_dic[uid]["room_id"])
    return "已添加{user}（{uid}）到关注列表。".format(user=user_dic[uid], uid=uid)
