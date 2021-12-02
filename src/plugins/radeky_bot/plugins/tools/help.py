from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import PrivateMessageEvent
from nonebot.permission import SUPERUSER
from nonebot.matcher import matchers

helper = on_command("help", permission=SUPERUSER, priority=5)


@helper.handle()
async def help_handler(bot: Bot, event: PrivateMessageEvent, state: T_State):
    # 获取设置了名称的插件列表
    await helper.finish('Hi there! 这里是radeky_bot命令文档v0.3.0\n'
        '机器人会识别以"." "。" "!" "！"开头的命令\n'
        '发送 .help <命令名称> 来查看具体命令用法\n'
        '目前支持的功能有：\n' + '' + '\n')
