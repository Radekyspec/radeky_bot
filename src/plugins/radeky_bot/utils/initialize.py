import os

from . import read_file
from . import write_file
from .. import config


async def check_initial():
    results = ["欢迎使用radeky_botV3，正在初始化配置文件…"]
    """
    try:
        os.listdir(os.path.realpath(config.radeky_dir))
        raw_users = await read_file.read_users()
        read_file.read_settings()
    except FileNotFoundError:
    """
    files = []
    for file in ["users.yml", "settings.ini"]:
        files.append(os.path.exists(os.path.join(os.path.realpath(config.radeky_dir), file)))
    if not all(files):
        await __generate_new()
        results.append('未找到配置文件，正在重新生成。')
    else:
        raw_users = await read_file.read_users()
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
    await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), 'settings.ini'),
                           '')
    await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), 'users.yml'),
                           '')


def __generate_temp_folder():
    os.makedirs(os.path.join(os.path.realpath(config.radeky_dir), 'temp'))
