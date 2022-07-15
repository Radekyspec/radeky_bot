from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import State, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ...utils import refresh, read_file, write_file
from ..tools.ws_monitor import Monitor

__plugin_name__ = 'rm'
__plugin_usage__ = r"""
用法：.rm <uid>

将对应主播的uid移出关注列表
"""

remove = on_command('rm', permission=SUPERUSER, priority=5)


@remove.handle()
async def del_uid(bot: Bot, event: PrivateMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    uid = str(message).strip()
    if uid:
        state["uid"] = uid


@remove.got("uid", prompt="请输入要取消关注的UID：")
async def get_uid(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    try:
        state["uid"] = str(state["uid"])
        state["uid"] = int(state["uid"])
    except ValueError:
        await remove.reject('UID只能为数字！请重新输入：')
    else:
        state["uid"] = str(state["uid"])
        user_removed = await remove_user_uid(state["uid"])
        await remove.finish(user_removed)


async def remove_user_uid(uid: str) -> str:
    try:
        user_dic = await read_file.read_users()
        setting_dic = read_file.read_settings()
    except FileNotFoundError:
        return '数据访问异常，取消关注失败。'

    del_user = user_dic[uid]

    try:
        del user_dic[uid]
        Monitor.remove(setting_dic[uid]["room_id"])
        del setting_dic[uid]
    except KeyError:
        return "输入数据错误，取消关注失败。"

    await write_file.write_users(user_dic)
    write_file.write_settings(setting_dic)
    await refresh.refresh_name()

    return '已经取消关注{user}（{uid}）。'.format(user=del_user, uid=uid)
