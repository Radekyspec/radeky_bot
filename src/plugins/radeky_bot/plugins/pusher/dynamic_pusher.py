# -*- coding:utf8 -*-
import nonebot
import json
import time
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
    for i in range(len(v_dict)):
        t = Pusher(list(v_dict.keys())[i], v_dict[list(v_dict.keys())[i]]["name"],
                   v_dict[list(v_dict.keys())[i]]["group"])
        await t.run()


class Pusher:
    def __init__(self, uid, name, group_list):
        self.uid = uid
        self.name = name
        self.group_list = group_list
        self.all_status = {}
        self.bot = nonebot.get_bot()

    async def run(self):
        self.all_status = await read_file.read_from_yaml(
            os.path.join(os.path.realpath(config.radeky_dir), "settings.yml"))
        await self.send_dynamic()
        return

    async def send_dynamic(self):
        dynamic_content = await self.get_dynamic_status(self.uid)
        if self.all_status[str(self.uid)]["Dynamic"] and dynamic_content:
            for content in dynamic_content:
                for each_group in self.group_list:
                    try:
                        await self.bot.call_api(api="send_group_msg", **{"group_id": each_group, "message": content})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send dynamic content of {error_uid} to group {group}!".format(
                                error_uid=self.uid, group=each_group))

    async def get_dynamic_status(self, uid):
        dy_url = "http://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history"
        param = {"host_uid": str(uid)}
        async with aiohttp.ClientSession() as session:
            async with session.get(dy_url, params=param) as res:
                res.encoding = "utf-8"
                res = await res.text()
        await session.close()
        cards_data = json.loads(res)
        try:
            cards_data = cards_data["data"]["cards"]
        except (KeyError, TypeError):
            return
        # Get successfully
        try:
            last_dynamic_str = await read_file.read(
                os.path.join(os.path.realpath(config.radeky_dir), "temp", str(uid) + "Dynamic"))
        except FileNotFoundError:
            last_dynamic_str = ""
        if last_dynamic_str == "":
            last_dynamic_str = cards_data[1]["desc"]["dynamic_id_str"]
        index = 0
        content_list = []
        photo_list = []
        all_photo = ""
        cards_data[0]["card"] = json.loads(cards_data[0]["card"])
        now_time = int(time.time())
        # card是字符串，需要重新解析
        while last_dynamic_str != cards_data[index]["desc"]["dynamic_id_str"]:
            try:
                # 动态时间戳校验
                if now_time - cards_data[index]["desc"]["timestamp"] > 300:
                    break
                if cards_data[index]["desc"]["type"] == 64:
                    # 发布新专栏
                    content_list.append(
                        "「{dynamic_user}」发了新专栏：\n"
                        "「{sc_title}」".format(dynamic_user=self.name,
                                              sc_title=cards_data[index]["card"]["title"]))
                elif cards_data[index]["desc"]["type"] == 8:
                    # 发布新视频
                    content_list.append("「{dynamic_user}」发了新视频，并说：{video_dynamic}\n"
                                        "{video_title}{video_pic}{video_desc}".format(
                        dynamic_user=self.name,
                        video_dynamic=cards_data[index]["card"]["dynamic"],
                        video_title=cards_data[index]["card"]["title"],
                        video_pic="[CQ:image,file={pic},cache=0,c=2]".format(pic=cards_data[index]["card"]["pic"]),
                        video_desc=cards_data[index]["card"]["desc"]))
                elif "description" in cards_data[index]["card"]["item"]:
                    # 带图新动态
                    for pic_info in cards_data[index]["card"]["item"]["pictures"]:
                        photo_list.append("[CQ:image,file={pic},cache=0,c=2]".format(pic=pic_info["img_src"]))
                    for photo in photo_list:
                        all_photo += photo
                    content_list.append("「{dynamic_user}」发了新动态： \n"
                                        "{dynamic_content}{dynamic_photos}".format(
                        dynamic_user=self.name,
                        dynamic_content=cards_data[index]["card"]["item"]["description"],
                        dynamic_photos=all_photo))
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

                    try:
                        # 转发用户动态
                        origin_name = cards_data[index]["card"]["origin_user"]["info"]["uname"]
                        origin_type, origin_title, photo_list, origin_desc = resolve_forward(cards_data[index]["card"])
                        for pic in photo_list:
                            all_photo += pic
                        content_list.append("「{dynamic_user}」转发了「{origin_name}」的{origin_type}并说： {forward_comment}\n\n"
                                            "「{origin_name}」的源{origin_type}：\n"
                                            "{origin_title}{origin_pic}{origin_desc}".format(
                            dynamic_user=self.name,
                            origin_name=origin_name,
                            forward_comment=cards_data[index]["card"]["item"]["content"],
                            origin_type=origin_type,
                            origin_title=origin_title,
                            origin_pic=all_photo,
                            origin_desc=origin_desc))
                    except KeyError:
                        # 转发番剧
                        origin_bangumi = json.loads(cards_data[index]["card"]["origin"])["apiSeasonInfo"]["title"]
                        content_list.append("「{dynamic_user}」转发了动画「{origin_bangumi}」并说：\n"
                                            "{forward_comment}".format(
                            dynamic_user=self.name, origin_bangumi=origin_bangumi,
                            forward_comment=cards_data[index]["card"]["item"]["content"]))
                else:
                    # 这个是不带图的自己发的动态
                    content_list.append(
                        "「{dynamic_user}」发了新动态：\n"
                        "{dynamic_info}".format(dynamic_user=self.name,
                                                dynamic_info=
                                                cards_data[index]["card"]["item"][
                                                    "content"]))
                content_list.append("本条动态地址为：https://t.bilibili.com/{dynamic_num}".format(
                    dynamic_num=cards_data[index]["desc"]["dynamic_id_str"]))
            except KeyError:
                nonebot.logger.error(
                    "Failed to resolve dynamic info of {error_uid}!".format(error_uid=uid))
            index += 1
            if len(cards_data) == index:
                break
            cards_data[index]["card"] = json.loads(cards_data[index]["card"])
        await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), "temp", str(uid) + "Dynamic"),
                               cards_data[0]["desc"]["dynamic_id_str"])
        return content_list
