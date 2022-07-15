import asyncio
import json
import time

import aiohttp

from . import read_file
from . import write_file


async def refresh_name() -> str:
    try:
        user_dic = await read_file.read_users()
        settings = read_file.read_settings()
    except FileNotFoundError:
        return f"文件读写错误，刷新失败。"
    if user_dic is None:
        return f"刷新失败。"

    if user_dic == "":
        await write_file.write_users(user_dic)
        return "由于关注列表无用户存在，缓存已清空。"
    else:
        uid_list = []
        for dict_key in user_dic.keys():
            uid_list.append(dict_key)
        uid_list = uid_list[:-1]
        for uid in uid_list:
            await asyncio.sleep(0.5)
            uid = str(uid)
            payload = {
                "mid": uid
            }
            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
            }
            async with aiohttp.request("GET", "https://api.bilibili.com/x/space/acc/info", params=payload,
                                       headers=headers) as res:
                res = await res.text()
                data = json.loads(res)
                if str(data["code"]) == "0":
                    user_dic[uid] = data["data"]["name"]
                    try:
                        settings[uid]["room_id"] = str(data["data"]["live_room"]["roomid"])
                    except TypeError:
                        settings[uid]["room_id"] = "0"
                else:
                    return str(data["message"])

        timestamp = int(round(time.time() * 1000))
        user_dic["timestamp"] = timestamp
        await write_file.write_users(user_dic)
        write_file.write_settings(settings)

        return "刷新完成。"
