import nonebot
import json
import aiohttp
import os
from ..tools.get_user_info import GetUserInfo
from ... import config
from ...utils import read_file, write_file
from nonebot.adapters.onebot.v11.exception import NetworkError

scheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job("interval", seconds=25, max_instances=20)
async def _():
    v_dict = await GetUserInfo().acquire()
    v_room_dict = await GetUserInfo().acquire_room()
    for i in range(len(v_dict)):
        room_id = await LivePusher.get_live_room_id(list(v_dict.keys())[i])
        if room_id and v_room_dict:
            t = LivePusher(v_room_dict)
            await t.scheduled_run(room_id, await LivePusher.get_live_data(room_id))


class LivePusher:
    def __init__(self, room_dict):
        self.room_dict = room_dict
        self.all_status = {}
        self.bot = nonebot.get_bot()

    @classmethod
    async def get_live_room_id(cls, uid):
        params = {"mid": uid, "jsonp": "jsonp"}
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.bilibili.com/x/space/acc/info", params=params) as res:
                res.encoding = "utf-8"
                res = await res.text()
        await session.close()
        data = json.loads(res)
        data = data["data"]
        room_id = None
        try:
            room_id = data["live_room"]["roomid"]
        except (TypeError, KeyError):
            pass
        return room_id

    @classmethod
    async def get_live_data(cls, room_id):
        params = {"device": "phone", "platform": "ios", "scale": "3", "build": "10000",
                  "room_id": str(room_id)}
        async with aiohttp.ClientSession() as session:
            async with session.get("http://api.live.bilibili.com/room/v1/Room/get_info", params=params) as res:
                res.encoding = "utf-8"
                res = await res.text()
        await session.close()
        return res

    async def scheduled_run(self, room_id, live_response_data):
        if str(await read_file.read(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"))) == "0":
            room_id, live_status = await self.get_live_status(room_id, live_response_data)
            if room_id and live_status:
                nonebot.logger.warning(
                    "[{room_id}]  Danmaku server has failed, fallback to default api.".format(room_id=room_id))
                await self.send_live(room_id, live_status)

    async def send_live(self, room_id, live_status):
        room_id = str(room_id)
        self.all_status = await read_file.read_from_yaml(
            os.path.join(os.path.realpath(config.radeky_dir), "settings.yml"))
        at_all = "[CQ:at,qq=all]"
        if self.all_status[str(self.room_dict[room_id]["uid"])]["Live"] and live_status == "LiveNow":
            cover = await self.get_cover(room_id)
            live_title = await self.get_title(room_id)
            if cover and live_title:
                for each_group in self.room_dict[room_id]["group"]:
                    message = "{live_user} 开始直播\n\n" \
                              "{live_title}\n" \
                              "传送门：https://live.bilibili.com/{rid}\n" \
                              "[CQ:image,file={live_cover},cache=0,c=2]".format(
                        live_user=self.room_dict[room_id]["name"],
                        live_title=live_title,
                        rid=str(room_id), live_cover=cover)
                    try:
                        if self.all_status[str(self.room_dict[room_id]["uid"])]["Atall"]:
                            message = at_all + message
                            await self.bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                             "message": message})
                        else:
                            await self.bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                             "message": message})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send live start message of {error_uid} to group {group}!".format(
                                error_uid=self.room_dict[room_id]["uid"], group=each_group))
        elif self.all_status[str(self.room_dict[room_id]["uid"])]["Live"] and live_status == "LiveEnd":
            cover = await self.get_cover(room_id)
            if cover:
                for each_group in self.room_dict[room_id]["group"]:
                    try:
                        message = "{live_user} 的直播结束了\n" \
                                  "[CQ:image,file={live_cover},cache=0,c=2]".format(
                            live_user=self.room_dict[room_id]["name"],
                            live_cover=cover)
                        await self.bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                         "message": message})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send live end message of {error_uid} to group {group}!".format(
                                error_uid=self.room_dict[room_id]["uid"], group=each_group))
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
                return str(room_id), "LiveNow"
            elif last_live_status != now_live_status and now_live_status != "1":
                return str(room_id), "LiveEnd"
            return "", ""
        else:
            return "", ""
