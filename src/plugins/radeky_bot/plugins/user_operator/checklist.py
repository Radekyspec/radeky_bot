import aiofiles
import os
import yaml
from ... import config
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.params import State
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'list'
__plugin_usage__ = r"""
用法：.list

发送轮询列表内的所有uid以及对应的主播用户名
"""
check = on_command("list", permission=SUPERUSER, priority=5)


@check.handle()
async def check_list(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    list_give = await display_all_uid()
    await check.finish(list_give)


async def display_all_uid() -> str:
    try:
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                 'r', encoding='utf-8') as u:
            user_dic = yaml.safe_load(await u.read())
            await u.close()
    except FileNotFoundError:
        return '查询失败。'
    name_list = []
    uid_list = []
    for dict_key in user_dic.keys():
        uid_list.append(dict_key)
        name_list.append(user_dic[dict_key])
    name_list = name_list[:-1]
    uid_list = uid_list[:-1]

    res = '列表中的用户有：\n'
    for i in range(len(uid_list)):
        res += str(uid_list[i]) + '：' + str(name_list[i]) + '\n'
    res = res[:-1]

    return res
