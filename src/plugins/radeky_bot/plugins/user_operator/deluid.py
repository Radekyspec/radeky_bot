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

__plugin_name__ = 'rm'
__plugin_usage__ = r"""
用法：.rm <uid>

将对应主播的uid移出关注列表
"""


remove = on_command('rm', permission=SUPERUSER, priority=5)


@remove.handle()
async def del_uid(bot: Bot, event: PrivateMessageEvent, state: T_State):
    uid = str(event.get_message()).strip()
    if uid:
        state["uid"] = uid


@remove.got("uid", prompt="请输入要取消关注的UID：")
async def get_uid(bot: Bot, event: PrivateMessageEvent, state: T_State):
    try:
        state["uid"] = int(state["uid"])
    except ValueError:
        await remove.reject('UID只能为数字！请重新输入：')
    else:
        state["uid"] = str(state["uid"])
        user_removed = await remove_user_uid(state["uid"])
        await remove.finish(user_removed)


async def remove_user_uid(uid: str) -> str:
    try:
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                 'r', encoding='utf-8') as du:
            user_dic = yaml.safe_load(await du.read())
            await du.close()
        async with aiofiles.open(
                os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'), 'r',
                encoding='utf-8') as ds:
            setting_dic = yaml.safe_load(await ds.read())
            await ds.close()
    except FileNotFoundError:
        return '数据访问异常，取消关注失败。'

    del_user = user_dic[uid]

    try:
        del user_dic[uid]
        del setting_dic[uid]
    except KeyError:
        return "输入数据错误，取消关注失败。"

    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                             'w', encoding='utf-8') as cu:
        await cu.write(yaml.dump(user_dic, allow_unicode=True))
        await cu.close()
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                             'w', encoding='utf-8') as cs:
        await cs.write(yaml.dump(setting_dic, allow_unicode=True))
        await cs.close()

    await refresh.refresh_name()
    return '已经取消关注{user}（{uid}）。'.format(user=del_user, uid=uid)
