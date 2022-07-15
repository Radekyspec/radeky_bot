import configparser
import os

import aiofiles
import yaml

from .. import config


async def write(path, content):
    async with aiofiles.open(path, "w") as w:
        await w.write(content)
        await w.close()
    return


async def write_users(content):
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), "users.yml"), "w") as wy:
        await wy.write(yaml.dump(content, allow_unicode=True))
        await wy.close()
    return


def write_settings(content):
    parser = configparser.ConfigParser()
    for section in content:
        parser[section] = content[section]
    with open(os.path.join(os.path.realpath(config.radeky_dir), "settings.ini"), "w", encoding="utf-8") as f:
        parser.write(f)
        f.close()
