from nonebot import on_request
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, GroupRequestEvent


__plugin_name__ = "自动加群 [Hidden]"
group_invite = on_request(priority=5)


@group_invite.handle()
async def group_handler(bot: Bot, event: GroupRequestEvent, state: T_State):
    if event.sub_type == "invite" and str(event.user_id) in bot.config.superusers:
        await bot.call_api(api="set_group_add_request", **{"flag": event.flag, "sub_type": "invite", "approve": True})
