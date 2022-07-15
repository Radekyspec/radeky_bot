from distutils.util import strtobool

from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent
from nonebot.params import State, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ...utils import write_file, read_file

__plugin_name__ = 'set'
__plugin_usage__ = r"""
用法：.set <uid> <setting_name> <values>

更改各种设置的开关（动态通知、改标题、@全体、直播通知）
各项设置名称如下，区分大小写
动态通知: bool = dynamic
标题通知: bool = title
@全体: bool = atall
直播通知: bool = live
间隔: int = interval
"""

settings = on_command("set", permission=SUPERUSER, priority=5)


@settings.handle()
async def handle_setting(bot: Bot, event: PrivateMessageEvent, state: T_State = State(),
                         message: Message = CommandArg()):
    setting = str(message).strip()
    if setting:
        set_list = setting.split()
        try:
            state["set_uid"] = str(set_list[0])
            state["set_info"] = str(set_list[1])
            state["set_status"] = str(set_list[2])
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
    if str(state["set_info"]) not in ["dynamic", "title", "live", "atall", "interval"]:
        await settings.reject("设置项有误！请重新输入：")


@settings.got("set_status", prompt="请输入需要改变的值：")
async def check_status(bot: Bot, event: PrivateMessageEvent, state: T_State = State()):
    set_values = str(state["set_status"])
    if state["set_info"] not in ["dynamic", "title", "live", "atall"]:
        pass
    else:
        set_values = bool(strtobool(set_values.lower()))
    result = await change_setting(str(state["set_uid"]), str(state["set_info"]), str(set_values))
    await settings.finish(result)


async def change_setting(uid: str, setting: str, status: str) -> str:
    setting_dic = read_file.read_settings()
    user_dic = await read_file.read_users()

    setting_dic[uid][setting] = status
    write_file.write_settings(setting_dic)

    return '{user}（{uid}）的{set}设置已更改为{status}'.format(user=user_dic[uid], uid=uid, set=setting, status=status)
