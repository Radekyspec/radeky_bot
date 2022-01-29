import aiofiles
import aiohttp
import json
import os
import time
import yaml
from .. import config


async def refresh_name() -> str:
    try:
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'), 'r', encoding='utf-8') as r:
            user_dic = yaml.safe_load(await r.read())
            await r.close()
    except FileNotFoundError:
        return f'文件读写错误，刷新失败。'
    if user_dic is None:
        return f'刷新失败。'

    if user_dic == '':
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'), 'w', encoding='utf-8') as x:
            await x.write(yaml.dump(user_dic, allow_unicode=True))
            await x.close()
        return '由于关注列表无用户存在，缓存已清空。'
    else:
        uid_list = []
        for dict_key in user_dic.keys():
            uid_list.append(dict_key)
        uid_list = uid_list[:-1]
        for uid in uid_list:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://api.bilibili.com/x/space/acc/info?mid='+str(uid)) as res:
                    res.encoding = 'utf-8'
                    res = await res.text()
            await session.close()
            data = json.loads(res)
            data = data['data']
            name = data['name']
            user_dic[uid] = name

        current_milli_time = lambda: int(round(time.time() * 1000))
        timestamp = current_milli_time()
        user_dic['timestamp'] = timestamp

        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'), 'w', encoding='utf-8') as g:
            await g.write(yaml.dump(user_dic, allow_unicode=True))
            await g.close()

        return f'刷新完成。'
