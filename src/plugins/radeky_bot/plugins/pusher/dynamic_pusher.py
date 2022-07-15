# -*- coding:utf8 -*-
import asyncio
import json
import os
import time

import aiohttp
import nonebot

from ... import config
from ...utils import read_file, write_file
from ...utils import sender
from ...utils.get_user_info import GetUserInfo

scheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job("interval", seconds=25, max_instances=20)
async def dynamic_pusher():
    v_dict = await GetUserInfo().acquire()
    t = [DynamicPusher(list(v_dict.keys())[i], v_dict[list(v_dict.keys())[i]]["name"],
                       v_dict[list(v_dict.keys())[i]]["group"]).run() for i in range(len(v_dict))]
    await asyncio.gather(*t)


class DynamicPusher:
    def __init__(self, uid, name, group_list):
        self.uid = str(uid)
        self.name = name
        self.group_list = group_list
        self.all_status = {}
        self.bot = nonebot.get_bot()

    async def run(self):
        self.all_status = read_file.read_settings()
        await self.send_dynamic()
        return

    async def send_dynamic(self):
        dynamic_content = await self.get_dynamic_status()
        if self.all_status[self.uid]["dynamic"] and dynamic_content:
            s = []
            for content in dynamic_content:
                for each_group in self.group_list:
                    s.append(sender.call_api(bot=self.bot, api="send_group_msg",
                                             kwargs={"group_id": each_group, "message": content}))
            await asyncio.gather(*s)

    async def get_dynamic_status(self):
        dy_url = "http://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history"
        param = {"host_uid": self.uid}
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(dy_url, params=param, headers=headers) as res:
                res.encoding = "utf-8"
                res = await res.text()
            await session.close()
        cards_data = json.loads(res)
        assert "code" in res, cards_data["code"] == 0
        try:
            cards_data = cards_data["data"]["cards"]
        except (KeyError, TypeError):
            return
        # Get successfully
        try:
            last_dynamic_str = await read_file.read(
                os.path.join(os.path.realpath(config.radeky_dir), "temp", str(self.uid) + "Dynamic"))
        except FileNotFoundError:
            last_dynamic_str = ""
        index = 0
        content_list = []
        photo_list = []
        all_photo = ""
        # card是字符串，需要重新解析
        # 替换原来字符串为解析后的值
        try:
            cards_data[index]["card"] = json.loads(cards_data[index]["card"])
            now_time = int(time.time())
            while last_dynamic_str != cards_data[index]["desc"]["dynamic_id_str"]:
                # 动态时间戳校验
                if now_time - cards_data[index]["desc"]["timestamp"] > 300:
                    break
                if cards_data[index]["desc"]["type"] == 64:
                    # 发布新专栏
                    all_content = "「{dynamic_user}」发了新专栏：\n「{sc_title}」".format(dynamic_user=self.name,
                                                                                sc_title=cards_data[index]["card"][
                                                                                    "title"])
                elif cards_data[index]["desc"]["type"] == 8:
                    # 发布新视频
                    all_content = "「{dynamic_user}」发了新视频，并说：{video_comment}\n\n" \
                                  "{video_title}{video_pic}{video_desc}".format(
                        dynamic_user=self.name,
                        video_comment=cards_data[index]["card"]["dynamic"],
                        video_title=cards_data[index]["card"]["title"],
                        video_pic="[CQ:image,file={pic},cache=0,c=2]".format(pic=cards_data[index]["card"]["pic"]),
                        video_desc=cards_data[index]["card"]["desc"])
                elif "description" in cards_data[index]["card"]["item"]:
                    # 带图新动态
                    for pic_info in cards_data[index]["card"]["item"]["pictures"]:
                        photo_list.append("[CQ:image,file={pic},cache=0,c=2]".format(pic=pic_info["img_src"]))
                    for photo in photo_list:
                        all_photo += photo
                    all_content = "「{dynamic_user}」发了新动态： \n" \
                                  "{dynamic_content}{dynamic_photos}".format(
                        dynamic_user=self.name,
                        dynamic_content=cards_data[index]["card"]["item"]["description"],
                        dynamic_photos=all_photo)
                    # 这个表示转发，原动态的信息在 cards-item-origin里面。里面又是一个超级长的字符串……
                elif "origin_user" in cards_data[index]["card"]:

                    def resolve_forward(message):
                        """
                        :param message: 传入的API返回值
                        :return: 动态类型，原动态标题，图片，简介
                        """
                        message = json.loads(message["origin"])
                        if "item" in message and "description" in message["item"]:
                            # 转发带图动态
                            origin_content = message["item"]["description"]
                            for pic_info in message["item"]["pictures"]:
                                photo_list.append("[CQ:image,file={pic},cache=0,c=2]".format(pic=pic_info["img_src"]))
                            return "动态", origin_content, photo_list, ""
                        elif "videos" in message:
                            # 转发视频
                            origin_title = message["title"]
                            origin_cover = "[CQ:image,file={pic},cache=0,c=2]".format(pic=message["pic"])
                            origin_desc = message["desc"]
                            return "视频", origin_title, [origin_cover], origin_desc
                        elif "item" in message and "content" in message["item"]:
                            # 转发纯文字动态
                            origin_content = message["item"]["content"]
                            return "动态", origin_content, [], ""
                        elif "id" in message:
                            # 转发专栏
                            origin_title = message["title"]
                            raw_origin_images = message["image_urls"]
                            for raw_image in raw_origin_images:
                                photo_list.append("[CQ:image,file={pic},cache=0,c=2]".format(pic=raw_image))
                            return "专栏", origin_title, photo_list, ""
                        elif "roomid" in message or "live_play_info" in message:
                            # 转发直播
                            area_name = "area_name" if "live_play_info" in message else "area_v2_name"
                            link = message["live_play_info"]["link"] if "live_play_info" in message else \
                                message["link"].split("?")[0]
                            message = message["live_play_info"] if "live_play_info" in message else message
                            return "直播", str(message["title"]), [
                                "[CQ:image,file={pic},cache=0,c=2]".format(pic=message["cover"])], " · ".join(
                                [message[area_name], message["watched_show"]]) + "\n传送门：" + link

                    try:
                        # 转发用户动态
                        origin_name = cards_data[index]["card"]["origin_user"]["info"]["uname"]
                        origin_type, origin_title, photo_list, origin_desc = resolve_forward(cards_data[index]["card"])
                        for pic in photo_list:
                            all_photo += pic
                        all_content = "「{dynamic_user}」转发了「{origin_name}」的{origin_type}并说： {forward_comment}\n\n" \
                                      "「{origin_name}」的源{origin_type}：\n" \
                                      "{origin_title}{origin_pic}{origin_desc}".format(
                            dynamic_user=self.name,
                            origin_name=origin_name,
                            forward_comment=cards_data[index]["card"]["item"]["content"],
                            origin_type=origin_type,
                            origin_title=origin_title,
                            origin_pic=all_photo,
                            origin_desc=origin_desc)
                    except KeyError:
                        # 转发番剧
                        origin_bangumi = json.loads(cards_data[index]["card"]["origin"])["apiSeasonInfo"]["title"]
                        all_content = "「{dynamic_user}」转发了动画「{origin_bangumi}」并说：\n" \
                                      "{forward_comment}".format(
                            dynamic_user=self.name, origin_bangumi=origin_bangumi,
                            forward_comment=cards_data[index]["card"]["item"]["content"])
                else:
                    # 这个是不带图的自己发的动态
                    all_content = "「{dynamic_user}」发了新动态：\n" \
                                  "{dynamic_info}".format(dynamic_user=self.name,
                                                          dynamic_info=
                                                          cards_data[index]["card"]["item"][
                                                              "content"])
                all_content += "\n\nhttps://t.bilibili.com/{dynamic_num}".format(
                    dynamic_num=cards_data[index]["desc"]["dynamic_id_str"])
                content_list.append(all_content)
                index += 1
                # 替换原来字符串为解析后的值
                cards_data[index]["card"] = json.loads(cards_data[index]["card"])
        except KeyError:
            pass

        await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), "temp", str(self.uid) + "Dynamic"),
                               cards_data[0]["desc"]["dynamic_id_str"])
        return content_list
