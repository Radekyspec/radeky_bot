import time

from . import read_file, refresh


class GetUserInfo:
    async def acquire(self):
        v_uid_list = await self.get_uid_list()
        v_name_list = await self.get_name_list()
        v_group_list = await self.get_group_list()
        v_dict = {}
        for i in range(len(v_uid_list)):
            v_dict.update(
                {
                    str(v_uid_list[i]): {
                        "name": v_name_list[i],
                        "group": v_group_list[i]
                    }
                }
            )
        return v_dict

    async def acquire_room(self):
        settings_dic = read_file.read_settings()
        v_dict = await self.acquire()
        v_room_dict = {}
        room_ids = {}
        for uid in settings_dic:
            room_ids.update({uid: settings_dic[uid]["room_id"]})
        if room_ids:
            for uid in room_ids:
                v_room_dict.update(
                    {
                        room_ids[uid]: {
                            "name": v_dict[uid]["name"],
                            "uid": uid,
                            "group": v_dict[uid]["group"],
                        }
                    }
                )
        return v_room_dict

    @staticmethod
    def room_list():
        settings_dic = read_file.read_settings()
        room_ids = []
        for uid in settings_dic:
            room_ids.append(settings_dic[uid]["room_id"])
        return room_ids

    @staticmethod
    async def get_name_list():
        users_dic = await read_file.read_users()
        all_name_list = []
        for dict_value in users_dic.values():
            all_name_list.append(dict_value)
        timestamp = int(all_name_list[-1])
        all_name_list = all_name_list[:-1]
        current_timestamp = int(round(time.time() * 1000))
        if current_timestamp - timestamp >= 604800000:
            await refresh.refresh_name()
            all_name_dic = await read_file.read_users()
            for dict_value in all_name_dic.values():
                all_name_list.append(dict_value)
            all_name_list = all_name_list[:-1]
        return all_name_list

    @staticmethod
    async def get_uid_list():
        users_dic = await read_file.read_users()
        uid_list = []
        uid_int = []
        for dict_key in users_dic:
            uid_list.append(dict_key)
        uid_list = uid_list[:-1]
        for uid in uid_list:
            uid = int(uid)
            uid_int.append(uid)
        return uid_int

    async def get_group_list(self, union=False):
        settings_dic = read_file.read_settings()
        v_uid_list = await self.get_uid_list()
        group_list = []

        async def __get_group_num(uid):
            group_list_in = []
            group_int = settings_dic[str(uid)]["group"].split(", ")
            for i in group_int:
                group_list_in.append(int(i))
            return group_list_in

        if union:
            for mid in v_uid_list:
                for group in await __get_group_num(mid):
                    group_list.append(group)
            return list(set(group_list))
        else:
            for mid in v_uid_list:
                group_list.append(await __get_group_num(mid))
            return group_list
