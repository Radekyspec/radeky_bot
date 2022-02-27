import aiohttp
import json
import os
import time
from ... import config
from ...utils import read_file, refresh


class GetUserInfo:
    async def acquire(self):
        v_uid_list = await self.get_uid_list()
        v_name_list = await self.get_name_list()
        v_group_list = await self.get_group_list()
        v_dict = {}
        for i in range(len(v_uid_list)):
            v_dict.update({str(v_uid_list[i]): {"name": v_name_list[i], "group": v_group_list[i]}})
        return v_dict

    async def acquire_room(self):
        v_dict = await self.acquire()
        v_room_dict = {}
        for uid in v_dict.keys():
            room_id = await self.get_live_room_id(uid)
            if room_id:
                v_room_dict.update(
                    {str(room_id): {"name": v_dict[uid]["name"], "uid": uid,
                                    "group": v_dict[uid]["group"]}})
        return v_room_dict

    async def get_live_room_id(self, uid):
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

    async def get_name_list(self):
        all_name_list = []
        all_name_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), "users.yml"))
        for dict_value in all_name_dic.values():
            all_name_list.append(dict_value)
        timestamp = int(all_name_list[-1])
        all_name_list = all_name_list[:-1]
        current_time = lambda: int(round(time.time() * 1000))
        current_timestamp = current_time()
        if current_timestamp - timestamp >= 604800000:
            await refresh.refresh_name()
            all_name_dic = await read_file.read_from_yaml(
                os.path.join(os.path.realpath(config.radeky_dir), "users.yml"))
            for dict_value in all_name_dic.values():
                all_name_list.append(dict_value)
            all_name_list = all_name_list[:-1]
        return all_name_list

    async def get_uid_list(self):
        uid_list = []
        uid_int = []
        all_uid_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), "users.yml"))
        for dict_key in all_uid_dic.keys():
            uid_list.append(dict_key)
        uid_list = uid_list[:-1]
        for uid in uid_list:
            uid = int(uid)
            uid_int.append(uid)
        return uid_int

    async def get_group_list(self):
        v_uid_list = await self.get_uid_list()
        group_list = []

        async def __get_group_num(uid):
            group_list = []
            group_dic = await read_file.read_from_yaml(
                os.path.join(os.path.realpath(config.radeky_dir), "settings.yml"))
            group_int = group_dic[str(uid)]["Group"]
            for i in group_int:
                group_list.append(int(i))
            return group_list

        for mid in v_uid_list:
            group_list.append(await __get_group_num(mid))
        return group_list
