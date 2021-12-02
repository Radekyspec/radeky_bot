import aiofiles
import os
import yaml
from .. import config


async def check_initial():
    results = ["欢迎使用radeky_botV3，正在初始化配置文件…"]
    try:
        os.listdir(os.path.realpath(config.radeky_dir))
        async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                                 'r', encoding='utf-8') as u:
            raw_users = yaml.safe_load(await u.read())
            await u.close()
        async with aiofiles.open(
                os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'), 'r',
                encoding='utf-8') as s:
            await s.close()
    except FileNotFoundError:
        await __generate_new()
        results.append('未找到配置文件，正在重新生成。')
    else:
        try:
            users = []
            for dict_key in raw_users.keys():
                users.append(dict_key)
            u_num = len(users)
            u_num -= 1
        except:
            u_num = 0
        if raw_users is None:
            u_num = 0
        results.append(f'配置文件载入成功，当前导入{u_num}个用户。')

    try:
        os.listdir(os.path.join(os.path.realpath(config.radeky_dir), 'temp'))
    except FileNotFoundError:
        __generate_temp_folder()

    results.append('初始化配置完成。')
    return results


async def __generate_new():
    try:
        os.makedirs(os.path.realpath(config.radeky_dir))
    except FileExistsError:
        pass
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'settings.yml'),
                             'w', encoding='utf-8') as ns:
        await ns.write('')
        await ns.close()
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'), 'w',
                             encoding='utf-8') as nu:
        await nu.write('')
        await nu.close()


def __generate_temp_folder():
    os.makedirs(os.path.join(os.path.realpath(config.radeky_dir), 'temp'))
