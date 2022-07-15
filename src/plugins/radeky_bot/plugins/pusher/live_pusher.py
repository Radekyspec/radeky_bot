import asyncio
import json
import os

import aiohttp
import nonebot

from ... import config
from ...utils import read_file, write_file
from ...utils import sender
from ...utils.get_user_info import GetUserInfo

scheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job("interval", seconds=25, max_instances=20)
async def live_pusher():
    u = GetUserInfo()
    v_dict = await u.acquire()
    room_ids = u.room_list()
    t = [LivePusher(u).scheduled_run(room_ids[i], await LivePusher.get_live_data(room_ids[i])) for i in
         range(len(v_dict))]
    await asyncio.gather(*t)


class LivePusher:
    LIVE_END = 0
    LIVE_NOW = 1

    def __init__(self, u):
        """
        :param u: instance of GetUserInfo class
        """
        self.u: GetUserInfo = u
        self.room_dict = {}
        self.all_status = {}
        self.bot = nonebot.get_bot()

    @staticmethod
    async def get_live_data(room_id):
        params = {"device": "phone", "platform": "ios", "scale": "3", "build": "10000",
                  "room_id": str(room_id)}
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.live.bilibili.com/room/v1/Room/get_info", params=params,
                                   headers=headers) as res:
                res.encoding = "utf-8"
                res = await res.text()
        await session.close()
        return res

    async def scheduled_run(self, room_id, live_response_data):
        if str(await read_file.read(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"))) == "0":
            self.room_dict = await self.u.acquire_room()
            room_id, live_status = await self.get_live_status(room_id, live_response_data)
            if room_id and live_status:
                await self.send_live(room_id, live_status)

    async def send_live(self, room_id, live_status):
        room_id = str(room_id)
        self.all_status = read_file.read_settings()
        at_all = "[CQ:at,qq=all]"
        if self.all_status[self.room_dict[room_id]["uid"]]["live"] and live_status == LivePusher.LIVE_NOW:
            cover = await self.get_cover(room_id)
            live_title = await self.get_title(room_id)
            if cover and live_title:
                message = "{live_user} 开始直播\n\n" \
                          "{live_title}\n" \
                          "传送门：https://live.bilibili.com/{rid}\n" \
                          "[CQ:image,file={live_cover},cache=0,c=2]".format(
                    live_user=self.room_dict[room_id]["name"],
                    live_title=live_title,
                    rid=str(room_id), live_cover=cover)
                if self.all_status[str(self.room_dict[room_id]["uid"])]["atall"]:
                    message = at_all + message
                s = [sender.call_api(bot=self.bot, api="send_group_msg", kwargs={"group_id": each_group,
                                                                                 "message": message}) for each_group in
                     self.room_dict[room_id]["group"]]
                await asyncio.gather(*s)
        elif self.all_status[self.room_dict[room_id]["uid"]]["live"] and live_status == LivePusher.LIVE_END:
            cover = await self.get_cover(room_id)
            if cover:
                message = "{live_user} 的直播结束了\n" \
                          "[CQ:image,file={live_cover},cache=0,c=2]".format(
                    live_user=self.room_dict[room_id]["name"],
                    live_cover=cover)
                s = [sender.call_api(bot=self.bot, api="send_group_msg", kwargs={"group_id": each_group,
                                                                                 "message": message}) for each_group in
                     self.room_dict[room_id]["group"]]
                await asyncio.gather(*s)
        return

    async def get_cover(self, room_id):
        res = await self.get_live_data(room_id)
        cover_data = json.loads(res)
        if str(cover_data["code"]) == "-412":
            return ""
        if str(cover_data["data"]["room_id"]) == str(room_id):
            try:
                cover_data = cover_data["data"]
                now_cover_status = cover_data["user_cover"]
            except KeyError:
                now_cover_status = ""
            return now_cover_status
        else:
            return ""

    async def get_title(self, room_id):
        res = await self.get_live_data(room_id)
        title_data = json.loads(res)
        if str(title_data["code"]) == "-412":
            return ""
        if str(title_data["data"]["room_id"]) == str(room_id):
            try:
                title_data = title_data["data"]
                now_title_data = title_data["title"]
            except KeyError:
                now_title_data = ""
                pass
            return now_title_data
        else:
            return ""

    async def get_live_status(self, room_id="", res=""):
        # 从api获取直播信息
        live_data = json.loads(res)
        if str(live_data["code"]) == "-412":
            return "", ""
        if str(live_data["data"]["room_id"]) == str(room_id):
            # 获取新的
            try:
                now_live_status = str(live_data["data"]["live_status"])
            except KeyError:
                now_live_status = "0"
                pass
            # 获取旧的
            try:
                last_live_status = await read_file.read(
                    os.path.join(os.path.realpath(config.radeky_dir), "temp", str(room_id) + "Live"))
            except FileNotFoundError:
                last_live_status = now_live_status
                pass
            # 写入新的
            await write_file.write(
                os.path.join(os.path.realpath(config.radeky_dir), "temp", str(room_id) + "Live"),
                now_live_status)
            if last_live_status != now_live_status and now_live_status == "1":
                return str(room_id), LivePusher.LIVE_NOW
            elif last_live_status != now_live_status and now_live_status != "1":
                return str(room_id), LivePusher.LIVE_END
            return "", ""
        else:
            return "", ""
