import os
from ... import config
from ...utils import write_file, read_file
from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.params import State, CommandArg
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'bind'
__plugin_usage__ = r"""
用法：.bind <uid> <QQ群号>

将主播对应uid与QQ群号绑定，绑定后机器人只会在相关的群聊发送提醒
"""

bind = on_command("bind", permission=SUPERUSER, priority=5)


@bind.handle()
async def bind_group(bot: Bot, event: PrivateMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    total = str(message).strip()
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
async def check_uid(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    try:
        state["bind_uid"] = str(state["bind_uid"])
        state["bind_uid"] = int(state["bind_uid"])
    except ValueError:
        await bind.reject("UID只能为数字！请重新输入：")
    else:
        state["bind_uid"] = str(state["bind_uid"])


@bind.got("group_list", prompt="请输入需要绑定的群聊，用空格分隔：")
async def check_group(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    if state["group_list"] is None:
        await bind.reject("请输入需要绑定的群聊，用空格分隔：")
    if not state["is_group_list"]:
        group_list = str(state["group_list"]).strip().split()
    else:
        group_list = str(state["group_list"])[2:-2].split("', '")
    bind_uid = state["bind_uid"]
    if bind_uid in group_list:
        await bind.reject("请勿输入相同的UID和群号！请重新输入群号，用空格分隔：")
    result = await bind_uid_to_group(bind_uid, group_list)
    await bind.finish(result)


async def bind_uid_to_group(uid: str, group: list) -> str:
    try:
        setting_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'))
        setting_dic[uid]['Group'] = group
        await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                                         setting_dic)
    except:
        return '文件读写异常，绑定失败。'

    user_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'))
    return '{user}（{uid}）已绑定至群聊{group}'.format(user=user_dic[uid], uid=uid, group=group)
