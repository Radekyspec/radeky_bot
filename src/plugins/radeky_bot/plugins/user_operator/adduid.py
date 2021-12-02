import aiofiles
import os
import yaml
from ... import config
from ...utils import refresh
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'add'
__plugin_usage__ = r"""
用法：.add <uid>

把uid对应的主播加入监控列表。
"""

add_uid = on_command("add", permission=SUPERUSER, priority=5)


@add_uid.handle()
async def get_uid(bot: Bot, event: PrivateMessageEvent, state: T_State):
    uid = str(event.get_message()).strip()
    if uid:
        state["uid"] = uid


@add_uid.got("uid", prompt="请输入需要关注用户的UID：")
async def handle_uid(bot: Bot, event: PrivateMessageEvent, state: T_State):
    uid = state["uid"]
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
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'), 'r',
                                 encoding='utf-8') as a:
            setting_dic = yaml.safe_load(await a.read())
            await a.close()
    except FileNotFoundError:
        setting_dic = {}
    if setting_dic is None:
        setting_dic = {}
    try:
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                 'r', encoding='utf-8') as u:
            user_dic = yaml.safe_load(await u.read())
            await u.close()
    except FileNotFoundError:
        user_dic = {}
    if user_dic is None:
        user_dic = {}

    user_dic[uid] = ''
    setting_dic[uid] = {'Group': [], 'Atall': False, 'Title': True, 'Dynamic': True, 'Live': True}

    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                             'w', encoding='utf-8') as ca:
        await ca.write(yaml.dump(setting_dic, allow_unicode=True))
        await ca.close()
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                             'w', encoding='utf-8') as cu:
        await cu.write(yaml.dump(user_dic, allow_unicode=True))
        await cu.close()

    await refresh.refresh_name()

    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                             'r', encoding='utf-8') as u:
        user_dic = yaml.safe_load(await u.read())
        await u.close()

    return '已添加{user}（{uid}）到关注列表。'.format(user=user_dic[uid], uid=uid)
