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
    VR_uid_list = await get_uid_list()
    VR_name_list = await get_name_list()
    VR_group_list = await get_group_list()
    for i in range(len(VR_uid_list)):
        t = Notification(VR_uid_list[i], VR_name_list[i], VR_group_list[i])
        await t.run()


async def get_name_list():
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


async def get_uid_list():
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


async def get_group_list():
    VR_uid_list = await get_uid_list()
    group_list = []
    for mid in VR_uid_list:
        group_list.append(await __get_group_num(mid))
    return group_list


async def get_live_data(room_id):
    params = {"device": "phone", "platform": "ios", "scale": "3", "build": "10000", "room_id": str(room_id)}
    async with aiohttp.ClientSession() as session:
        async with session.get('http://api.live.bilibili.com/room/v1/Room/get_info', params=params) as res:
            res.encoding = 'utf-8'
            res = await res.text()
    await session.close()
    return res


async def get_live_room_id(mid):
    params = {"mid": str(mid), "jsonp": "jsonp"}
    async with aiohttp.ClientSession() as session:
        async with session.get('http://api.bilibili.com/x/space/acc/info', params=params) as res:
            res.encoding = 'utf-8'
            res = await res.text()
    await session.close()
    data = json.loads(res)
    data = data['data']
    roomid = 0
    try:
        roomid = data['live_room']['roomid']
    except:
        pass
    return roomid


class Notification:
    def __init__(self, uid, name, group_list):
        self.uid = uid
        self.name = name
        self.group_list = group_list
        self.bot = nonebot.get_bot()

    async def run(self):
        await self.send_notification(self.bot)
        return

    async def send_notification(self, bot: Bot):
        room_id = await get_live_room_id(self.uid)
        self.live_response_data = await get_live_data(room_id)
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

        title = await self.get_title(room_id)
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

        live_status = await self.get_live_status(room_id)
        if all_status[str(self.uid)]['Live'] and live_status:
            cover = await self.get_cover(room_id)
            if cover:
                for each_group in self.group_list:
                    try:
                        if all_status[str(self.uid)]['Atall']:
                            message = "{at}{live_user} 开始直播\n\n" \
                                      "{live_title}\n" \
                                      "传送门：https://live.bilibili.com/{rid}\n" \
                                      "[CQ:image,file={live_cover},cache=0,c=2]".format(
                                at=at_all, live_user=self.name,
                                live_title=live_status,
                                rid=str(room_id), live_cover=cover)
                            await bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                        "message": message})
                        else:
                            message = "{live_user} 开始直播\n\n" \
                                      "{live_title}\n" \
                                      "传送门：https://live.bilibili.com/{rid}\n" \
                                      "[CQ:image,file={live_cover},cache=0,c=2]".format(
                                live_user=self.name,
                                live_title=live_status,
                                rid=str(room_id), live_cover=cover)
                            await bot.call_api(api="send_group_msg", **{"group_id": each_group,
                                                                        "message": message})
                    except NetworkError:
                        nonebot.logger.error(
                            "Failed to send live notification of {error_uid} to group {group}!".format(
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
                if now_time - cards_data[index]['desc']['timestamp'] > 125:
                    break
                if cards_data[index]['desc']['type'] == 64:
                    # 发布新专栏
                    content_list.append(
                        '{dynamic_user}发了新专栏「{sc_title}」'.format(dynamic_user=self.name,
                                                                 sc_title=cards_data[index]['card']['title']))
                elif cards_data[index]['desc']['type'] == 8:
                    # 发布新视频
                    content_list.append('{dynamic_user}发了新视频「{video_title}」并说： {video_comment}'.format(
                        dynamic_user=self.name, video_title=cards_data[index]['card']['title'],
                        video_comment=cards_data[index]['card']['dynamic']))
                elif 'description' in cards_data[index]['card']['item']:
                    # 带图新动态
                    for pic_info in cards_data[index]['card']['item']['pictures']:
                        photo_list.append('[CQ:image,file={pic},cache=0,c=2]'.format(pic=pic_info['img_src']))
                    for photo in photo_list:
                        all_photo += photo
                    content_list.append('{dynamic_user}发了新动态： {dynamic_content}{dynamic_photos}'.format(
                        dynamic_user=self.name,
                        dynamic_content=cards_data[index]['card']['item']['description'],
                        dynamic_photos=all_photo))
                # 这个表示转发，原动态的信息在 cards-item-origin里面。里面又是一个超级长的字符串……
                elif 'origin_user' in cards_data[index]['card']:
                    try:
                        # 转发用户动态
                        origin_name = cards_data[index]['card']['origin_user']['info']['uname']
                    except KeyError:
                        # 转发番剧
                        origin_name = json.loads(cards_data[index]['card']['origin'])['apiSeasonInfo']['title']
                    content_list.append('{dynamic_user}转发了「{origin_user}」的动态并说： {forward_comment}'.format(
                        dynamic_user=self.name, origin_user=origin_name,
                        forward_comment=cards_data[index]['card']['item']['content']))
                else:
                    # 这个是不带图的自己发的动态
                    content_list.append(
                        '{dynamic_user}发了新动态：{dynamic_info}'.format(dynamic_user=self.name,
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
        if live_data['data']["room_id"] == room_id:
            try:
                async with aiofiles.open(
                        os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + 'Live'),
                        'r') as f:
                    last_live_str = await f.read()
                    await f.close()
            except FileNotFoundError:
                last_live_str = '0'
                pass
            try:
                live_data = live_data['data']
                now_live_status = str(live_data['live_status'])
                live_data = live_data['title']
            except KeyError:
                now_live_status = '0'
                pass
            async with aiofiles.open(
                    os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + 'Live'),
                    'w') as f:
                await f.write(now_live_status)
                await f.close()
            if last_live_str != '1':
                if now_live_status == '1':
                    return live_data
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

    async def get_title(self, room_id):
        res = self.live_response_data
        title_data = json.loads(res)
        if title_data['data']["room_id"] == room_id:
            try:
                async with aiofiles.open(
                        os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + 'Title'),
                        'r') as t:
                    old_title = await t.read()
                    await t.close()
            except FileNotFoundError:
                old_title = ''
                pass
            try:
                title_data = title_data['data']
                now_title_data = title_data['title']
            except KeyError:
                now_title_data = ''
                pass
            async with aiofiles.open(
                    os.path.join(os.path.realpath(config.radeky_dir), 'temp', str(room_id) + "Title"), 'w') as t:
                await t.write(now_title_data)
                await t.close()
            if old_title != '' and now_title_data != '':
                if old_title != now_title_data:
                    return now_title_data
            return ''
        else:
            return ''
