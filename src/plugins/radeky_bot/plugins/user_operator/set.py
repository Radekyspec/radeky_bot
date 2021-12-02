import aiofiles
import os
import yaml
from ... import config
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import PrivateMessageEvent
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
async def handle_setting(bot: Bot, event: PrivateMessageEvent, state: T_State):
    setting = str(event.get_message()).strip()
    if setting:
        set_list = setting.split()
        try:
            state["set_uid"] = set_list[0]
            state["set_info"] = set_list[1]
            state["set_status"] = set_list[2]
        except IndexError:
            pass


@settings.got("set_uid", prompt="请输入需要设置的UID：")
async def check_info(bot: Bot, event: PrivateMessageEvent, state: T_State):
    try:
        state["set_uid"] = int(state["set_uid"])
    except ValueError:
        await settings.reject("UID只能为数字！请重新输入：")
    else:
        state["set_uid"] = str(state["set_uid"])


@settings.got("set_info", prompt="请输入需要设置的项（区分大小写）：")
async def check_uid(bot: Bot, event: PrivateMessageEvent, state: T_State):
    if state["set_info"] not in ["Dynamic", "Title", "Live", "Atall"]:
        await settings.reject("设置项有误！请重新输入：")


@settings.got("set_status", prompt="请输入需要改变的值：")
async def check_status(bot: Bot, event: PrivateMessageEvent, state: T_State):
    set_status = str(state["set_status"]).lower().capitalize()
    if set_status == "True":
        set_status = True
    elif set_status == "False":
        set_status = False
    else:
        await settings.reject("类型值错误！请重新输入：")
    result = await change_setting(state["set_uid"], state["set_info"], set_status)
    await settings.finish(result)


async def change_setting(uid: str, setting: str, status: bool) -> str:
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                             'r', encoding='utf-8') as s:
        setting_dic = yaml.safe_load(await s.read())
        await s.close()
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                             'r', encoding='utf-8') as u:
        user_dic = yaml.safe_load(await u.read())
        await u.close()

    setting_dic[uid][setting] = status
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                             'w', encoding='utf-8') as t:
        await t.write(yaml.dump(setting_dic, allow_unicode=True))
        await t.close()

    return '{user}（{uid}）的{set}设置已更改为{status}'.format(user=user_dic[uid], uid=uid, set=setting, status=status)
