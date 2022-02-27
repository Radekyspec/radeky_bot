import asyncio
from nonebot import require, logger
import os
from ... import config
from .dm import BiliDM, LivePusher
from .get_user_info import GetUserInfo
from ...utils import read_file, write_file

scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job("interval", seconds=30, max_instances=20)
async def monitor():
    if str(await read_file.read(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"))) == "0":
        logger.warning("[Danmaku]  Connection closed. Reconnecting...")
        await stop_ws()
        await start_ws()
        await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"), "1")


async def start_ws():
    room_id_list = []
    v_dict = await GetUserInfo().acquire()
    for uid in v_dict.keys():
        room_id_list.append(await LivePusher.get_live_room_id(uid))
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(BiliDM.start(room_id_list), loop)


async def stop_ws():
    await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"), "0")
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(BiliDM.stop(), loop)
