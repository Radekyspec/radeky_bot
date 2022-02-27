import os
from ... import config
from ...utils import write_file, read_file
from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.typing import T_State
from nonebot.params import State, CommandArg
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.permission import SUPERUSER

__plugin_name__ = 'set'
__plugin_usage__ = r"""
用法：.set <uid> <setting_name> <true/false>

更改各种设置的开关（动态通知、改标题、@全体、直播通知）
各项设置名称如下，区分大小写
动态通知: Dynamic
标题通知: Title
@全体: Atall
直播通知: Live
"""

settings = on_command("set", permission=SUPERUSER, priority=5)


@settings.handle()
async def handle_setting(bot: Bot, event: PrivateMessageEvent, state: T_State = State(),
                         message: Message = CommandArg()):
    setting = str(message).strip()
    if setting:
        set_list = setting.split()
        try:
            state["set_uid"] = set_list[0]
            state["set_info"] = set_list[1]
            state["set_status"] = set_list[2]
        except IndexError:
            pass


@settings.got("set_uid", prompt="请输入需要设置的UID：")
async def check_info(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    try:
        state["set_uid"] = str(state["set_uid"])
        state["set_uid"] = int(state["set_uid"])
    except ValueError:
        await settings.reject("UID只能为数字！请重新输入：")
    else:
        state["set_uid"] = str(state["set_uid"])


@settings.got("set_info", prompt="请输入需要设置的项（区分大小写）：")
async def check_uid(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    if str(state["set_info"]) not in ["Dynamic", "Title", "Live", "Atall"]:
        await settings.reject("设置项有误！请重新输入：")


@settings.got("set_status", prompt="请输入需要改变的值：")
async def check_status(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    set_status = str(state["set_status"]).lower().capitalize()
    if set_status == "True":
        set_status = True
    elif set_status == "False":
        set_status = False
    else:
        await settings.reject("类型值错误！请重新输入：")
    result = await change_setting(str(state["set_uid"]), str(state["set_info"]), set_status)
    await settings.finish(result)


async def change_setting(uid: str, setting: str, status: bool) -> str:
    setting_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'))
    user_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'))

    setting_dic[uid][setting] = status
    await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                                     setting_dic)

    return '{user}（{uid}）的{set}设置已更改为{status}'.format(user=user_dic[uid], uid=uid, set=setting, status=status)
