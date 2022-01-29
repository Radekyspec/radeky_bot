# -*- coding:utf8 -*-
import nonebot
import json
import time
import aiofiles
import aiohttp
import os
import yaml
from ... import config
from ...utils import refresh
from nonebot.adapters.cqhttp.exception import NetworkError
from nonebot.adapters import Bot

scheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job('interval', seconds=25, max_instances=20)
async def _():
    VR_uid_list, VR_name_list, VR_group_list = await GetUserInfo().run()
    for i in range(len(VR_uid_list)):
        t = Notification(VR_uid_list[i], VR_name_list[i], VR_group_list[i])
        await t.run()


class GetUserInfo:
    async def run(self):
        VR_uid_list = await self.get_uid_list()
        VR_name_list = await self.get_name_list()
        VR_group_list = await self.get_group_list()
        return VR_uid_list, VR_name_list, VR_group_list

    async def get_name_list(self):
        all_name_list = []
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                 'r', encoding='utf-8') as g:
            all_name_dic = yaml.safe_load(await g.read())
            await g.close()
        for dict_value in all_name_dic.values():
            all_name_list.append(dict_value)
        timestamp = int(all_name_list[-1])
        all_name_list = all_name_list[:-1]
        current_time = lambda: int(round(time.time() * 1000))
        current_timestamp = current_time()
        if current_timestamp - timestamp >= 604800000:
            await refresh.refresh_name()
            async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                     'r', encoding='utf-8') as g:
                all_name_dic = yaml.safe_load(await g.read())
                await g.close()
            for dict_value in all_name_dic.values():
                all_name_list.append(dict_value)
            all_name_list = all_name_list[:-1]
        return all_name_list

    async def get_uid_list(self):
        uid_list = []
        uid_int = []
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                 'r', encoding='utf-8') as u:
            all_uid_dic = yaml.safe_load(await u.read())
            await u.close()
        for dict_key in all_uid_dic.keys():
            uid_list.append(dict_key)
        uid_list = uid_list[:-1]
        for uid in uid_list:
            uid = int(uid)
            uid_int.append(uid)
        return uid_int

    async def get_group_list(self):
        VR_uid_list = await self.get_uid_list()
        group_list = []

        async def __get_group_num(uid):
            group_list = []
            async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                                     mode='r', encoding='utf-8') as r:
                group_dic = yaml.safe_load(await r.read())
                await r.close()
            group_int = group_dic[str(uid)]['Group']
            for i in group_int:
                group_list.append(int(i))
            return group_list

        for mid in VR_uid_list:
            group_list.append(await __get_group_num(mid))
        return group_list


class Notification:
    def __init__(self, uid, name, group_list):
        self.uid = uid
        self.name = name
        self.group_list = group_list
        self.room_id = ""
        self.live_response_data = ""
        self.bot = nonebot.get_bot()

    async def run(self):
        async def get_live_data(room_id):
            params = {"device": "phone", "platform": "ios", "scale": "3", "build": "10000",
                      "room_id": str(room_id)}
            async with aiohttp.ClientSession() as session:
                async with session.get('http://api.live.bilibili.com/room/v1/Room/get_info', params=params) as res:
                    res.encoding = 'utf-8'
                    res = await res.text()
            await session.close()
            return res

        async def get_live_room_id(uid):
            params = {"mid": uid, "jsonp": "jsonp"}
            async with aiohttp.ClientSession() as session:
                async with session.get('http://api.bilibili.com/x/space/acc/info', params=params) as res:
                    res.encoding = 'utf-8'
                    res = await res.text()
            await session.close()
            data = json.loads(res)
            data = data['data']
            room_id = 0
            try:
                room_id = data['live_room']['roomid']
            except KeyError:
                pass
            return room_id

        self.room_id = await get_live_room_id(self.uid)
        self.live_response_data = await get_live_data(self.room_id)
        await self.send_notification(self.bot)
        return

    async def send_notification(self, bot: Bot):
        at_all = '[CQ:at,qq=all]'
        async with aiofiles.open(
                os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'), 'r',
                encoding='utf-8') as t:
            all_status = yaml.safe_load(await t.read())
            await t.close()

        if all_status[str(self.uid)]['Dynamic']:
            dynamic_content = await self.get_dynamic_status(self.uid)
            for content in dynamic_content:
                for each_group in self.group_list:
                    try:
                        await bot.call_api(api="send_group_msg", **{"group_id": each_group, "message": content})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send dynamic content of {error_uid} to group {group}!".format(
                                error_uid=self.uid, group=each_group))

        title = await self.compare_title(self.room_id)
        if all_status[str(self.uid)]['Title'] and title:
            for each_group in self.group_list:
                try:
                    await bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                "message": "{t_user} 更改了直播间标题为：{t_title}".format(
                                                                    t_user=self.name,
                                                                    t_title=title)})
                except NetworkError:
                    nonebot.logger.error(
                        "Failed to send changed title of {error_uid} to group {group}!".format(
                            error_uid=self.uid, group=each_group))

        live_status = await self.get_live_status(self.room_id)
        if all_status[str(self.uid)]['Live'] and live_status == "LiveNow":
            cover = await self.get_cover(self.room_id)
            live_title = self.get_title(self.room_id)
            if cover and live_title:
                for each_group in self.group_list:
                    try:
                        if all_status[str(self.uid)]['Atall']:
                            message = "{at}{live_user} 开始直播\n\n" \
                                      "{live_title}\n" \
                                      "传送门：https://live.bilibili.com/{rid}\n" \
                                      "[CQ:image,file={live_cover},cache=0,c=2]".format(
                                at=at_all, live_user=self.name,
                                live_title=live_title,
                                rid=str(self.room_id), live_cover=cover)
                            await bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                        "message": message})
                        else:
                            message = "{live_user} 开始直播\n\n" \
                                      "{live_title}\n" \
                                      "传送门：https://live.bilibili.com/{rid}\n" \
                                      "[CQ:image,file={live_cover},cache=0,c=2]".format(
                                live_user=self.name,
                                live_title=live_title,
                                rid=str(self.room_id), live_cover=cover)
                            await bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                        "message": message})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send live start message of {error_uid} to group {group}!".format(
                                error_uid=self.uid, group=each_group))
        elif all_status[str(self.uid)]['Live'] and live_status == "LiveEnd":
            cover = await self.get_cover(self.room_id)
            if cover:
                for each_group in self.group_list:
                    try:
                        message = "{live_user} 的直播结束了\n" \
                                  "[CQ:image,file={live_cover},cache=0,c=2]".format(
                            live_user=self.name,
                            live_cover=cover)
                        await bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                    "message": message})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send live end message of {error_uid} to group {group}!".format(
                                error_uid=self.uid, group=each_group))
        return

    async def get_dynamic_status(self, uid):
        dy_url = 'http://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history'
        param = {"host_uid": str(uid)}
        async with aiohttp.ClientSession() as session:
            async with session.get(dy_url, params=param) as res:
                res.encoding = 'utf-8'
                res = await res.text()
        await session.close()
        cards_data = json.loads(res)
        try:
            cards_data = cards_data['data']['cards']
        except KeyError:
            exit()
        # Get successfully
        try:
            async with aiofiles.open(
                    os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(uid) + 'Dynamic'),
                    'r') as f:
                last_dynamic_str = await f.read()
                await f.close()
        except FileNotFoundError:
            last_dynamic_str = ''
        if last_dynamic_str == '':
            last_dynamic_str = cards_data[1]['desc']['dynamic_id_str']
        index = 0
        content_list = []
        photo_list = []
        all_photo = ''
        cards_data[0]['card'] = json.loads(cards_data[0]['card'])
        now_time = int(time.time())
        # card是字符串，需要重新解析
        while last_dynamic_str != cards_data[index]['desc']['dynamic_id_str']:
            try:
                # 动态时间戳校验
                if now_time - cards_data[index]['desc']['timestamp'] > 300:
                    break
                if cards_data[index]['desc']['type'] == 64:
                    # 发布新专栏
                    content_list.append(
                        '「{dynamic_user}」发了新专栏：\n'
                        '「{sc_title}」'.format(dynamic_user=self.name,
                                              sc_title=cards_data[index]['card']['title']))
                elif cards_data[index]['desc']['type'] == 8:
                    # 发布新视频
                    content_list.append('「{dynamic_user}」发了新视频，并说：{video_dynamic}\n'
                                        '{video_title}{video_pic}{video_desc}'.format(
                        dynamic_user=self.name,
                        video_dynamic=cards_data[index]['card']['dynamic'],
                        video_title=cards_data[index]['card']['title'],
                        video_pic="[CQ:image,file={pic},cache=0,c=2]".format(pic=cards_data[index]["card"]["pic"]),
                        video_desc=cards_data[index]["card"]["desc"]))
                elif 'description' in cards_data[index]['card']['item']:
                    # 带图新动态
                    for pic_info in cards_data[index]['card']['item']['pictures']:
                        photo_list.append('[CQ:image,file={pic},cache=0,c=2]'.format(pic=pic_info['img_src']))
                    for photo in photo_list:
                        all_photo += photo
                    content_list.append('「{dynamic_user}」发了新动态： \n'
                                        '{dynamic_content}{dynamic_photos}'.format(
                        dynamic_user=self.name,
                        dynamic_content=cards_data[index]['card']['item']['description'],
                        dynamic_photos=all_photo))
                # 这个表示转发，原动态的信息在 cards-item-origin里面。里面又是一个超级长的字符串……
                elif 'origin_user' in cards_data[index]['card']:
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
                                photo_list.append('[CQ:image,file={pic},cache=0,c=2]'.format(pic=pic_info['img_src']))
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
                        origin_name = cards_data[index]['card']['origin_user']['info']['uname']
                        origin_type, origin_title, photo_list, origin_desc = resolve_forward(cards_data[index]['card'])
                        for pic in photo_list:
                            all_photo += pic
                        content_list.append("「{dynamic_user}」转发了「{origin_name}」的{origin_type}并说： {forward_comment}\n\n"
                                            "「{origin_name}」的源{origin_type}：\n"
                                            "{origin_title}{origin_pic}{origin_desc}".format(
                            dynamic_user=self.name,
                            origin_name=origin_name,
                            forward_comment=cards_data[index]['card']['item']['content'],
                            origin_type=origin_type,
                            origin_title=origin_title,
                            origin_pic=all_photo,
                            origin_desc=origin_desc))
                    except KeyError:
                        # 转发番剧
                        origin_bangumi = json.loads(cards_data[index]['card']['origin'])['apiSeasonInfo']['title']
                        content_list.append('「{dynamic_user}」转发了动画「{origin_bangumi}」并说：\n'
                                            '{forward_comment}'.format(
                            dynamic_user=self.name, origin_bangumi=origin_bangumi,
                            forward_comment=cards_data[index]['card']['item']['content']))
                else:
                    # 这个是不带图的自己发的动态
                    content_list.append(
                        '「{dynamic_user}」发了新动态：\n'
                        '{dynamic_info}'.format(dynamic_user=self.name,
                                                dynamic_info=
                                                cards_data[index]['card']['item'][
                                                    'content']))
                content_list.append('本条动态地址为：https://t.bilibili.com/{dynamic_num}'.format(
                    dynamic_num=cards_data[index]['desc']['dynamic_id_str']))
            except KeyError:
                nonebot.logger.error(
                    "Failed to resolve dynamic info of {error_uid}!".format(error_uid=uid))
            index += 1
            if len(cards_data) == index:
                break
            cards_data[index]['card'] = json.loads(cards_data[index]['card'])
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(uid) + 'Dynamic'),
                                 'w') as f:
            await f.write(cards_data[0]['desc']['dynamic_id_str'])
            await f.close()
        return content_list

    async def get_live_status(self, room_id):
        res = self.live_response_data
        live_data = json.loads(res)
        if live_data["data"]["room_id"] == room_id:
            try:
                async with aiofiles.open(
                        os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + 'Live'),
                        'r') as f:
                    last_live_status = await f.read()
                    await f.close()
            except FileNotFoundError:
                last_live_status = '0'
                pass
            try:
                now_live_status = str(live_data["data"]['live_status'])
            except KeyError:
                now_live_status = '0'
                pass
            async with aiofiles.open(
                    os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + 'Live'),
                    'w') as f:
                await f.write(now_live_status)
                await f.close()
            if last_live_status != '1' and now_live_status == '1':
                return "LiveNow"
            elif last_live_status == "1" and now_live_status != "1":
                return "LiveEnd"
            return ''
        else:
            return ''

    async def get_cover(self, room_id):
        res = self.live_response_data
        cover_data = json.loads(res)
        if cover_data['data']['room_id'] == room_id:
            try:
                cover_data = cover_data['data']
                now_cover_status = cover_data['user_cover']
            except KeyError:
                now_cover_status = ''
            return now_cover_status
        else:
            return ''

    def get_title(self, room_id):
        res = self.live_response_data
        title_data = json.loads(res)
        if title_data['data']["room_id"] == room_id:
            try:
                title_data = title_data['data']
                now_title_data = title_data['title']
            except KeyError:
                now_title_data = ''
                pass
            return now_title_data
        else:
            return ''

    async def compare_title(self, room_id):
        try:
            async with aiofiles.open(
                    os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + 'Title'),
                    'r') as t:
                old_title = await t.read()
                await t.close()
        except FileNotFoundError:
            old_title = ''
            pass
        now_title_data = self.get_title(room_id)
        async with aiofiles.open(
                os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + "Title"), 'w') as t:
            await t.write(now_title_data)
            await t.close()
        if old_title != '' and now_title_data != '' and old_title != now_title_data:
            return now_title_data
        return ''
