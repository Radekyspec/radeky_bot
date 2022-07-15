import asyncio
import os

from .dm import BiliDM
from ... import config
from ...utils import write_file
from ...utils.get_user_info import GetUserInfo


class Monitor:
    instances = {}

    def __init__(self):
        room_id_list = list(filter(lambda a: True if a != "0" else False, GetUserInfo().room_list()))
        for room_id in room_id_list:
            self.instances[room_id] = BiliDM(room_id)

    async def start_ws(self):
        await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"), "1")
        loop = asyncio.get_event_loop()
        for room_id in self.instances:
            asyncio.run_coroutine_threadsafe(self.instances[room_id].startup(),
                                             loop)

    async def stop_ws(self):
        await write_file.write(os.path.join(os.path.realpath(config.radeky_dir), "temp", "ws_status"), "0")
        loop = asyncio.get_event_loop()
        for room_id in self.instances:
            asyncio.run_coroutine_threadsafe(self.instances[room_id].stop(),
                                             loop)

    @classmethod
    def add(cls, room_id: str):
        cls.instances[room_id] = BiliDM(room_id)
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(cls.instances[room_id].startup(), loop)

    @classmethod
    def remove(cls, room_id: str):
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(cls.instances[room_id].stop(), loop)
        del cls.instances[room_id]
