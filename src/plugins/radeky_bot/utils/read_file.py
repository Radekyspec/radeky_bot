import configparser
import os

import aiofiles
import yaml

from .. import config
from distutils.util import strtobool


async def read(path):
    async with aiofiles.open(path, "r") as r:
        content = await r.read()
        await r.close()
    return content


async def read_users():
    async with aiofiles.open(os.path.join(os.path.realpath(config.radeky_dir), "users.yml"), "r",
                             encoding="utf-8") as ry:
        content = yaml.safe_load(await ry.read())
        await ry.close()
    return content


def read_settings():
    parser = configparser.ConfigParser()
    parser.read(os.path.join(os.path.realpath(config.radeky_dir), "settings.ini"), encoding="utf-8")
    parser = dict(parser)
    for uid in parser:
        parser[uid] = dict(parser[uid])
        for options in parser[uid]:
            if options not in ["group", "room_id", "interval"]:
                parser[uid][options] = bool(strtobool(parser[uid][options]))
    del parser["DEFAULT"]
    return parser
