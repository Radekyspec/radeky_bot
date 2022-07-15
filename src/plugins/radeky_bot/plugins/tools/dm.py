import asyncio
import json
import os
import traceback

import aiohttp
import brotli
import websockets
from nonebot import logger

from ..pusher.live_pusher import LivePusher
from ... import config
from ...utils import write_file, read_file
from ...utils.get_user_info import GetUserInfo


class BiliDM:
    WS = None

    def __init__(self, room_id):
        self.room_id = str(room_id)
        self.wss_url = "wss://"
        self.closed = False

    async def get_key(self):
        url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo"
        payload = {
            "id": self.room_id,
            "type": 0,
        }
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        async with aiohttp.request("GET", url, params=payload, headers=headers) as resp:
            resp = json.loads(await resp.text())
            self.wss_url = self.wss_url + resp["data"]["host_list"][0]["host"] + "/sub"
            return resp["data"]["token"]

    async def startup(self):
        key = await self.get_key()
        payload = "".join(
            json.dumps(
                {
                    "uid": 0,
                    "roomid": int(self.room_id),
                    "protover": 3,
                    "platform": "web",
                    "type": 2,
                    "key": key
                }
            ).split(" "))
        header_op = "001000010000000700000001"
        header_len = ("0" * (8 - len(hex(len(payload) + 16)[2:])) + hex(len(payload) + 16)[2:]) if len(
            hex(len(payload) + 16)[2:]) <= 8 else ...
        header = header_len + header_op + bytes(str(payload), encoding="utf-8").hex()
        async for aws in websockets.connect(self.wss_url):
            self.WS = aws
            await aws.send(bytes.fromhex(header))
            logger.success("[{room_id}]  Connected to danmaku server.".format(room_id=self.room_id))
            tasks = [self.heart_beat(aws), self.receive_dm(aws)]
            try:
                await asyncio.gather(*tasks)
            except websockets.ConnectionClosed:
                if not self.closed:
                    logger.warning("[{room_id}]  Disconnected to danmaku server.".format(room_id=self.room_id))
                    continue
                break

    async def heart_beat(self, websockets):
        hb = "00000010001000010000000200000001"
        while True:
            await asyncio.sleep(30)
            await websockets.send(bytes.fromhex(hb))
            logger.debug("[{room_id}][HEARTBEAT]  Send HeartBeat.".format(room_id=self.room_id))

    async def receive_dm(self, websockets):
        while True:
            receive_text = await websockets.recv()
            if receive_text:
                await self.process_dm(receive_text)
            await asyncio.sleep(0.5)

    async def process_dm(self, data, is_decompressed=False):
        # 获取数据包的长度，版本和操作类型
        packet_len = int(data[:4].hex(), 16)
        ver = int(data[6:8].hex(), 16)
        op = int(data[8:12].hex(), 16)

        # 有的时候可能会两个数据包连在一起发过来，所以利用前面的数据包长度判断，
        if len(data) > packet_len:
            task = asyncio.create_task(self.process_dm(data[packet_len:]))
            data = data[:packet_len]
            await task

        # brotli 压缩后的数据
        if ver == 3 and not is_decompressed:
            data = brotli.decompress(data[16:])
            await self.process_dm(data, is_decompressed=True)
            return

        # ver 为1的时候为进入房间后或心跳包服务器的回应。op 为3的时候为房间的人气值。
        if ver == 1 and op == 3:
            logger.debug(
                "[{room_id}][ATTENTION]  {attention}".format(room_id=self.room_id, attention=int(data[16:].hex(), 16)))
            return

        # ver 不为2也不为1目前就只能是0了，也就是普通的 json 数据。
        # op 为5意味着这是通知消息，cmd 基本就那几个了。
        if op == 5:
            try:
                jd = json.loads(data[16:].decode("utf-8", errors="ignore"))
                if jd["cmd"] == "LIVE":
                    try:
                        last_live_status = str(await read_file.read(
                            os.path.join(os.path.realpath(config.radeky_dir), "temp", str(self.room_id) + "Live")))
                    except FileNotFoundError:
                        last_live_status = "0"
                    await write_file.write(
                        os.path.join(os.path.realpath(config.radeky_dir), "temp", str(self.room_id) + "Live"), "1")
                    if last_live_status != "1":
                        t = LivePusher(GetUserInfo())
                        t.room_dict = await t.u.acquire_room()
                        await t.send_live(self.room_id, LivePusher.LIVE_NOW)
                    logger.debug(self.room_id + " LiveNow")
                elif jd["cmd"] == "PREPARING":
                    try:
                        last_live_status = str(await read_file.read(
                            os.path.join(os.path.realpath(config.radeky_dir), "temp", str(self.room_id) + "Live")))
                    except FileNotFoundError:
                        last_live_status = "1"
                    await write_file.write(
                        os.path.join(os.path.realpath(config.radeky_dir), "temp", str(self.room_id) + "Live"), "0")
                    if last_live_status != "0":
                        t = LivePusher(GetUserInfo())
                        t.room_dict = await t.u.acquire_room()
                        await t.send_live(self.room_id, LivePusher.LIVE_END)
                    logger.debug(self.room_id + " LiveEnd")
                else:
                    logger.debug(f"[{self.room_id}][OTHER] " + jd["cmd"])
            except Exception:
                logger.error(traceback.format_exc())

    async def stop(self):
        self.closed = True
        if self.WS is not None:
            await self.WS.close()
