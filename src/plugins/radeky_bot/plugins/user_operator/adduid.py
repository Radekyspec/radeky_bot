import os
from ... import config
from ...utils import refresh, read_file, write_file
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.params import State, CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'add'
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
    try:
        setting_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'))
    except FileNotFoundError:
        setting_dic = {}
    if setting_dic is None:
        setting_dic = {}
    try:
        user_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'))
    except FileNotFoundError:
        user_dic = {}
    if user_dic is None:
        user_dic = {}

    user_dic[uid] = ''
    setting_dic[uid] = {'Group': [], 'Atall': False, 'Title': True, 'Dynamic': True, 'Live': True, "room_id": "0"}

    await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                                     setting_dic)
    await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                     user_dic)
    await refresh.refresh_name()

    user_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'))
    return '已添加{user}（{uid}）到关注列表。'.format(user=user_dic[uid], uid=uid)
