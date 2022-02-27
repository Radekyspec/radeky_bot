import aiohttp
import json
import os
import time
from . import read_file
from . import write_file
from .. import config


async def refresh_name() -> str:
    try:
        user_dic = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'))
        settings = await read_file.read_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'))
    except FileNotFoundError:
        return f'文件读写错误，刷新失败。'
    if user_dic is None:
        return f'刷新失败。'

    if user_dic == '':
        await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                         user_dic)
        return '由于关注列表无用户存在，缓存已清空。'
    else:
        uid_list = []
        for dict_key in user_dic.keys():
            uid_list.append(dict_key)
        uid_list = uid_list[:-1]
        for uid in uid_list:
            payload = {
                "mid": str(uid)
            }
            async with aiohttp.ClientSession() as session:
                async with session.get('http://api.bilibili.com/x/space/acc/info', params=payload) as res:
                    res.encoding = 'utf-8'
                    res = await res.text()
            await session.close()
            data = json.loads(res)
            user_dic[uid] = data['data']['name']
            settings[uid]["room_id"] = data["data"]["live_room"]["roomid"]

        current_milli_time = lambda: int(round(time.time() * 1000))
        timestamp = current_milli_time()
        user_dic['timestamp'] = timestamp

        await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                         user_dic)
        await write_file.write_from_yaml(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                                         settings)

        return '刷新完成。'
