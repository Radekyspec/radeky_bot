import json

import aiohttp
from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.params import State, CommandArg
from nonebot.rule import to_me
from nonebot.typing import T_State

send_picture = on_command("setu", rule=to_me(), priority=1)
send_picture_cn = on_command("色图", rule=to_me(), priority=1)
send_picture_cn_2 = on_command("涩图", rule=to_me(), priority=1)
send_picture_cn_3 = on_command("来点色图", rule=to_me(), priority=1)
send_picture_cn_4 = on_command("来点涩图", rule=to_me(), priority=1)


async def sex_handler(bot: Bot, event: GroupMessageEvent, state: T_State = State(), message=None):
    args = str(message).strip().split()
    print(args)
    if args:
        state["r18"] = args
        if "R18" in state["r18"]:
            tags = state["r18"]
            state["r18"] = []
            for tag in tags:
                state["r18"].append(tag if tag != "R18" else tag.lower())
        if "R-18" in state["r18"]:
            tags = state["r18"]
            state["r18"] = []
            for tag in tags:
                state["r18"].append(tag if tag != "R-18" else "r18")
        if "r-18" in state["r18"]:
            tags = state["r18"]
            state["r18"] = []
            for tag in tags:
                state["r18"].append(tag if tag != "r-18" else "r18")
    else:
        state["r18"] = []
    message_list = await pic_sender(state["r18"])
    for message in message_list:
        await bot.call_api(api="send_group_msg", **{"group_id": event.group_id, "message": message})


async def pic_sender(r18: list) -> list:
    url = "https://api.lolicon.app/setu/v2"
    payload = {
        "r18": "1" if "r18" in r18 else "2",
        "proxy": "pixiv.qiscord.com",
    }
    if payload["r18"] == "1":
        r18.remove("r18")
    if len(r18) >= 1:
        payload["tag"] = "|".join(r18)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=payload) as resp:
            resp = await resp.text()
            try:
                resp = json.loads(resp)["data"][0]
            except IndexError:
                return ["库中没有与关键词匹配的记录，请更换关键词再试。"]
    await session.close()

    tags = "，".join(resp["tags"])
    sex_photo_desc = ["[CQ:image,file={photo_link},type=flash,cache=0,c=2]".format(photo_link=resp["urls"]["original"]),
                      """标题：{title}
作品 pid：{artwork_uid}
作者：{author}
作者 uid：{author_uid}
作品标签：{tags}
是否 R18：{is_r18}""".format(photo_link=resp["urls"]["original"], title=resp["title"],
                          artwork_uid=resp["pid"], author=resp["author"], author_uid=resp["uid"],
                          tags=tags, is_r18="是" if resp["r18"] else "否")]
    return sex_photo_desc


@send_picture.handle()
async def en_handler(bot: Bot, event: GroupMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    await sex_handler(bot, event, state, message)
    await send_picture.finish()


@send_picture_cn.handle()
async def cn_handler(bot: Bot, event: GroupMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    await sex_handler(bot, event, state, message)
    await send_picture_cn.finish()


@send_picture_cn_2.handle()
async def cn_handler(bot: Bot, event: GroupMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    await sex_handler(bot, event, state, message)
    await send_picture_cn_2.finish()


@send_picture_cn_3.handle()
async def cn_handler(bot: Bot, event: GroupMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    await sex_handler(bot, event, state, message)
    await send_picture_cn_3.finish()


@send_picture_cn_4.handle()
async def cn_handler(bot: Bot, event: GroupMessageEvent, state: T_State = State(), message: Message = CommandArg()):
    await sex_handler(bot, event, state, message)
    await send_picture_cn_4.finish()
