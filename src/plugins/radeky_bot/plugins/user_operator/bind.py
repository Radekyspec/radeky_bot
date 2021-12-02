import aiofiles
import os
import yaml
from ... import config
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'bind'
__plugin_usage__ = r"""
用法：.bind <uid> <QQ群号>

将主播对应uid与QQ群号绑定，绑定后机器人只会在相关的群聊发送提醒
"""

bind = on_command("bind", permission=SUPERUSER, priority=5)


@bind.handle()
async def bind_group(bot: Bot, event: PrivateMessageEvent, state: T_State):
    total = str(event.get_message()).strip()
    state["is_group_list"] = False
    if total:
        total_list = total.split()
        try:
            state["bind_uid"] = total_list[0]
            state["group_list"] = total_list[1:] if total_list[1:] else None
            state["is_group_list"] = True if state["group_list"] else False
        except KeyError:
            pass


@bind.got("bind_uid", prompt="请输入需要绑定的UID：")
async def check_uid(bot: Bot, event: PrivateMessageEvent, state: T_State):
    try:
        state["bind_uid"] = int(state["bind_uid"])
    except ValueError:
        await bind.reject("UID只能为数字！请重新输入：")
    else:
        state["bind_uid"] = str(state["bind_uid"])


@bind.got("group_list", prompt="请输入需要绑定的群聊，用空格分隔：")
async def check_group(bot: Bot, event: PrivateMessageEvent, state: T_State):
    if state["group_list"] is None:
        await bind.reject("请输入需要绑定的群聊，用空格分隔：")
    if not state["is_group_list"]:
        group_list = str(state["group_list"]).strip().split()
    else:
        group_list = state["group_list"]
    bind_uid = state["bind_uid"]
    if bind_uid in group_list:
        await bind.reject("请勿输入相同的UID和群号！请重新输入群号，用空格分隔：")
    result = await bind_uid_to_group(bind_uid, group_list)
    await bind.finish(result)


async def bind_uid_to_group(uid: str, group: list) -> str:
    try:
        async with aiofiles.open(
                os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'), 'r',
                encoding='utf-8') as b:
            setting_dic = yaml.safe_load(await b.read())
            await b.close()
        setting_dic[uid]['Group'] = group
        async with aiofiles.open(
                os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'), 'w',
                encoding='utf-8') as cb:
            await cb.write(yaml.dump(setting_dic, allow_unicode=True))
            await cb.close()
    except:
        return '文件读写异常，绑定失败。'

    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                             'r', encoding='utf-8') as u:
        user_dic = yaml.safe_load(await u.read())
        await u.close()

    return '{user}（{uid}）已绑定至群聊{group}'.format(user=user_dic[uid], uid=uid, group=group)
