import asyncio
import json
import os
import traceback
import zlib
from aiowebsocket.converses import AioWebSocket
from typing import Optional


class BiliDM:
    def __init__(self, room_id):
        self.room_id = str(room_id)
        self.wss_url = "wss://broadcastlv.chat.bilibili.com/sub"
        self.fail_time = 0
        self.fail = False

    async def startup(self):
        data_raw = "000000{headerLen}0010000100000007000000017b22726f6f6d6964223a{roomid}7d"
        data_raw = data_raw.format(headerLen=hex(27 + len(self.room_id))[2:],
                                   roomid="".join(map(lambda x: hex(ord(x))[2:], list(self.room_id))))
        async with AioWebSocket(self.wss_url) as aws:
            converse = aws.manipulator
            await converse.send(bytes.fromhex(data_raw))
            print("[{room_id}]  Connected to danmaku server.".format(room_id=self.room_id))
            tasks = [self.heart_beat(converse), self.receive_dm(converse)]
            await asyncio.gather(*tasks)
        return

    async def heart_beat(self, websockets):
        hb = "00000010001000010000000200000001"
        while not self.fail:
            await asyncio.sleep(30)
            await websockets.send(bytes.fromhex(hb))
            self.fail_time += 1
            print("[{room_id}][HEARTBEAT]  Send HeartBeat.".format(room_id=self.room_id))
            if self.fail_time > 5 and not self.fail:
                print("[{room_id}]  Too many attempts. Danmaku server is no longer available.".format(
                    room_id=self.room_id))
                self.fail = True

    async def receive_dm(self, websockets):
        while not self.fail:
            receive_text = await websockets.receive()
            if receive_text:
                await self.process_dm(receive_text)

    async def process_dm(self, data, is_decompressed=False):
        # 获取数据包的长度，版本和操作类型
        packet_len = int(data[:4].hex(), 16)
        ver = int(data[6:8].hex(), 16)
        op = int(data[8:12].hex(), 16)

        # 有的时候可能会两个数据包连在一起发过来，所以利用前面的数据包长度判断，
        if len(data) > packet_len:
            await self.process_dm(data[packet_len:])
            data = data[:packet_len]

        # 有时会发送过来 zlib 压缩的数据包，这个时候要去解压。
        if ver == 2 and not is_decompressed:
            data = zlib.decompress(data[16:])
            await self.process_dm(data, is_decompressed=True)
            return

        # ver 为1的时候为进入房间后或心跳包服务器的回应。op 为3的时候为房间的人气值。
        if ver == 1 and op == 3:
            print(
                "[{room_id}][ATTENTION]  {attention}".format(room_id=self.room_id, attention=int(data[16:].hex(), 16)))
            self.fail_time = 0
            return

        # ver 不为2也不为1目前就只能是0了，也就是普通的 json 数据。
        # op 为5意味着这是通知消息，cmd 基本就那几个了。
        if op == 5:
            try:
                jd = json.loads(data[16:].decode("utf-8", errors="ignore"))
                if jd["cmd"] == "DANMU_MSG":
                    print(f"[{self.room_id}][DANMAKU] " + jd["info"][2][1] + ": " + jd["info"][1])
                elif jd["cmd"] == "LIVE":
                    print(f"[{self.room_id}][LIVE] " + jd["info"][2][1] + ": " + jd["info"][1])
                elif jd["cmd"] == "PREPARING":
                    print(f"[{self.room_id}][PREPARING] " + jd["info"][2][1] + ": " + jd["info"][1])
                else:
                    print(f"[{self.room_id}][OTHER] " + jd["cmd"])
            except Exception:
                print(traceback.format_exc())

    @classmethod
    async def start(cls, room_list: Optional[list] = None):
        if room_list is None:
            room_list = ["371798", "290889"]
        cls.room_list = room_list
        tasks = []
        for room_id in room_list:
            tasks.append(BiliDM(room_id).startup())
        await asyncio.gather(*tasks)

    # TODO 修改ws连接关闭函数
    @classmethod
    def stop(cls):
        for task in asyncio.current_task():
            print("Cancelling the task {}: {}".format(id(task), task.cancel()))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(BiliDM.start([21452505]))