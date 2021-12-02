# -*- coding:utf8 -*-
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import aiofiles
import asyncio
import nonebot
import os
import yaml
import urllib.parse
from apscheduler.schedulers.blocking import BlockingScheduler
from nonebot.adapters import Bot
from nonebot.adapters.cqhttp import NetworkError

scheduler = nonebot.require("nonebot_plugin_apscheduler").scheduler
job = BlockingScheduler()


@scheduler.scheduled_job('interval', seconds=60, max_instances=10, coalesce=True, id="bili_rec")
def rec_upload():
    user_list = ['23110731-松雪安娜', '399531-奶油熊子炖菜', '22934139-EC-03C型试作机', '22727902-鼎鼎子']
    group_list = [151330941, 578210482, 1049388996, 171440318]
    for i in range(len(user_list)):
        job.pause_job("bili_rec")
        asyncio.run(VideoUploader(user_list[i], group_list[i]).run())
        job.resume_job("bili_rec")


class VideoUploader:
    def __init__(self, rec_user, group_id):
        self.rec_user = rec_user
        self.rec_path = os.path.join('/', 'home', 'pi', 'record', rec_user)
        self.group_id = group_id
        self.link_endpoint = "https://rec-backups-1301436793.cos.ap-guangzhou.myqcloud.com/"
        self.cos = CosUpload("rec-backups-1301436793")
        self.bot = nonebot.get_bot()

    async def run(self):
        await self.uploader(self.bot)
        return

    async def uploader(self, bot: Bot):
        file_names = await self.get_record_file()
        # 查看是否录制完成
        # 录制完成且未分段就发送
        # 否则不发送
        if file_names:
            qq_tasks, cos_tasks, link = [], [], ""
            for file_name in file_names:
                await self.add_to_known(file_name)
                link += file_name + "：" + self.link_endpoint + urllib.parse.quote(
                    self.rec_user.encode('utf-8')) + "/" + urllib.parse.quote(file_name.encode('utf-8')) + "\n"
                qq_tasks.append(bot.call_api(api="upload_group_file",
                                             **{"group_id": self.group_id,
                                                "file": os.path.join(self.rec_path, file_name),
                                                "name": file_name}))
                cos_tasks.append(self.cos.upload_files(self.rec_user, os.path.join(self.rec_path, file_name)))
            link = link[:-1]
            try:
                await bot.call_api(api="send_group_msg",
                                   **{"group_id": self.group_id,
                                      "message": "本次录播已同步至对象存储COS并保留21天，下载直链：\n"
                                                 "{link}".format(link=link)})
            except NetworkError:
                nonebot.logger.error(
                    "Failed to send cos notice of {user} to {group}".format(user=self.rec_user, group=self.group_id))
            try:
                for qq_task in qq_tasks:
                    await qq_task
            except NetworkError:
                nonebot.logger.error(
                    "Failed to upload qq file of {user} to {group}".format(user=self.rec_user, group=self.group_id))
            try:
                for cos_task in cos_tasks:
                    await cos_task
            except NetworkError:
                nonebot.logger.error(
                    "Failed to upload cos file of {user} to {group}".format(user=self.rec_user, group=self.group_id))
        return

    async def get_record_file(self) -> list:
        path_files = os.listdir(self.rec_path)
        try:
            path_files.remove("file_sizes.yml")
            path_files.remove("known_files.yml")
        except:
            pass
        for file in path_files:
            if os.path.getsize(os.path.join(self.rec_path, file)) <= 2097152 and await self.check_recording(file):
                os.remove(os.path.join(self.rec_path, file))
        path_files = os.listdir(self.rec_path)
        try:
            path_files.remove("file_sizes.yml")
            path_files.remove("known_files.yml")
        except:
            pass
        known_files = await self.get_known_list()

        # 只有一个录像
        if len(path_files) == 1:
            # 确认录制完毕且未发送
            qq_uploaded_files = await self.get_group_file(self.bot)
            cos_uploaded_files = await self.cos.get_cos_uploaded_files(self.rec_user)

            if await self.check_recording(path_files[0]) and path_files[
                0] not in known_files and not await self.check_COS_uploading(
                path_files[0]) and not await self.check_QQ_uploading(path_files[0]):
                return path_files

            if path_files[0] in qq_uploaded_files:
                await self.update_qq_file_info(path_files[0])

            # 应对奇妙的上传失败问题
            if path_files[0] not in cos_uploaded_files and await self.check_recording(
                    path_files[0]) and path_files[
                0] in known_files and await self.cos.check_upload_list():
                await self.cos.upload_files(self.rec_user, os.path.join(self.rec_path, path_files[0]))

            if path_files[0] in known_files and await self.check_recording(
                    path_files[0]) and await self.check_COS_uploading(
                path_files[0]) and await self.check_QQ_uploading(path_files[0]):
                os.remove(os.path.join(self.rec_path, path_files[0]))
            # 只有一个文件但没完成录制/已经上传
            return []
        # 多于一个文件
        elif len(path_files) > 1:
            qq_uploaded_files = await self.get_group_file(self.bot)
            cos_uploaded_files = await self.cos.get_cos_uploaded_files(self.rec_user)
            # 有上传过的视频
            if len(known_files) != 0:
                # 删除旧的录像文件
                for present_file in path_files:
                    if present_file in qq_uploaded_files:
                        await self.update_qq_file_info(present_file)

                    if present_file not in cos_uploaded_files and await self.check_recording(
                            present_file) and present_file in known_files and await self.cos.check_upload_list():
                        # 应对奇妙的上传失败问题
                        await self.cos.upload_files(self.rec_user, os.path.join(self.rec_path, present_file))

                    if present_file in known_files and await self.check_recording(
                            present_file) and await self.check_COS_uploading(
                        present_file) and await self.check_QQ_uploading(present_file):
                        os.remove(os.path.join(self.rec_path, present_file))

                exist_files = os.listdir(self.rec_path)
                try:
                    exist_files.remove("file_sizes.yml")
                    exist_files.remove("known_files.yml")
                except:
                    pass
            else:
                # 无上传过的视频, 添加所有视频
                exist_files = path_files
            # 删除后存在1个以上的视频
            if len(exist_files) > 1:
                # 查看分段设置
                if await self.check_cutting():
                    # 忽略分段设置
                    record_status = []
                    for exist_file in exist_files:
                        if await self.check_recording(exist_file) and exist_file not in known_files:
                            result = True
                        else:
                            result = False
                        record_status.append(result)
                    if all(record_status):
                        # 全部录制完成后发送
                        return exist_files
                    # 录制未完成
                    return []
                else:
                    # 确认分段，不发送。
                    return []
            # 删除后剩下一个文件且已经录制完毕
            elif len(exist_files) == 1 and await self.check_recording(exist_files[0]):
                return exist_files
            # 删除后剩下一个文件但未完成录制/删除后没有剩余文件
            return []
        else:
            # 目录下没有文件
            return []

    async def check_recording(self, f_name) -> bool:
        try:
            async with aiofiles.open(os.path.join(self.rec_path, 'file_sizes.yml'), 'r', encoding='utf-8') as s:
                file_sizes = yaml.safe_load(await s.read())
                await s.close()
        except:
            print("Cannot open config file, operation cancelled.")
            return False

        try:
            session_id = file_sizes["file_search"][f_name]
        except:
            return False

        if file_sizes["video_data"][session_id]['FileClosed']:
            await asyncio.sleep(1)
            return True
        else:
            return False

    async def check_cutting(self) -> bool:
        try:
            async with aiofiles.open(os.path.join(self.rec_path, "file_sizes.yml"), 'r', encoding='utf-8') as c:
                file_data = yaml.safe_load(await c.read())
                await c.close()
        except:
            print("Error occurred while reading the config, skipped.")
            return False
        try:
            cut = bool(file_data["ignore_cutting"])
        except:
            return False
        return cut

    async def get_known_list(self) -> list:
        try:
            async with aiofiles.open(os.path.join(self.rec_path, 'known_files.yml'), 'r', encoding='utf-8') as k:
                known_list = yaml.safe_load(await k.read())
                await k.close()
        except:
            known_list = []
        if known_list is None:
            known_list = []
        return known_list

    async def add_to_known(self, f_name):
        try:
            async with aiofiles.open(os.path.join(self.rec_path, 'known_files.yml'), 'r', encoding='utf-8') as k:
                known_files = yaml.safe_load(await k.read())
                await k.close()
        except FileNotFoundError:
            known_files = []
        if known_files is None:
            known_files = []
        known_files.append(f_name)
        async with aiofiles.open(os.path.join(self.rec_path, 'known_files.yml'), 'w', encoding='utf-8') as ck:
            await ck.write(yaml.dump(known_files, allow_unicode=True))
            await ck.close()
        return

    async def check_COS_uploading(self, f_name) -> bool:
        try:
            async with aiofiles.open(os.path.join(self.rec_path, 'file_sizes.yml'), 'r') as u:
                file_details = yaml.safe_load(await u.read())
                await u.close()
        except:
            print("No such config file, skipped.")
            return False

        try:
            session_id = file_details["file_search"][f_name]
        except:
            print("No such file record, skipped.")
            return False
        cos: bool = file_details["video_data"][session_id]["COSUploaded"]
        return cos

    async def check_QQ_uploading(self, f_name) -> bool:
        try:
            async with aiofiles.open(os.path.join(self.rec_path, 'file_sizes.yml'), 'r') as u:
                file_details = yaml.safe_load(await u.read())
                await u.close()
        except:
            print("No such config file, skipped.")
            return False

        try:
            session_id = file_details["file_search"][f_name]
        except:
            print("No such file record, skipped.")
            return False
        qq: bool = file_details["video_data"][session_id]["QQUploaded"]
        return qq

    async def get_group_file(self, bot: Bot) -> list:
        res = await bot.call_api(api="get_group_root_files", **{"group_id": self.group_id})
        res = res["files"]
        if res is None:
            return []
        group_file_list = []
        for detail in res:
            group_file_list.append(detail["file_name"])
        return group_file_list

    async def update_qq_file_info(self, f_name):
        async with aiofiles.open(os.path.join(self.rec_path, "file_sizes.yml"), 'r') as p:
            file_details = yaml.safe_load(await p.read())
            await p.close()
        session_id = file_details["file_search"][f_name]
        file_details["video_data"][session_id]["QQUploaded"] = True
        async with aiofiles.open(os.path.join(self.rec_path, "file_sizes.yml"), 'w') as wp:
            await wp.write(yaml.dump(file_details, allow_unicode=True))
            await wp.close()
        return


class CosUpload:
    def __init__(self, bucket):
        # 设置用户属性, 包括 secret_id, secret_key, region等。
        # Appid 已在CosConfig中移除，请在参数 Bucket 中带上 Appid。Bucket 由 BucketName-Appid 组成
        secret_id = 'AKIDHNDm45qKXTAaw2rRmrfEWXHm0xd2B3dw'
        # 替换为用户的 SecretId，请登录访问管理控制台进行查看和管理，https://console.cloud.tencent.com/cam/capi
        secret_key = '5tQggOq0tWsxlIYXFhsnRoukJbeRxDDw'
        # 替换为用户的 SecretKey，请登录访问管理控制台进行查看和管理，https://console.cloud.tencent.com/cam/capi
        region = 'ap-guangzhou'
        # 替换为用户的 region，已创建桶归属的region可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
        scheme = 'https'
        # 指定使用 http/https 协议来访问 COS，默认为 https，可不填
        self.rec_path = os.path.join('/', 'home', 'pi', 'record')
        self.bucket = bucket
        self.config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Scheme=scheme)

        # 2. 获取客户端对象
        self.client = CosS3Client(self.config)

    def upload_percentage(self, consumed_bytes, total_bytes):
        """进度条回调函数，计算当前上传的百分比

        :param consumed_bytes: 已经上传的数据量
        :param total_bytes: 总数据量
        """
        if total_bytes:
            rate = int(100 * (float(consumed_bytes) / float(total_bytes)))
            print('\r{0}% '.format(rate))
            sys.stdout.flush()
        return

    async def upload_files(self, rec_user: str, f_path: str):
        # 上传由 '/' 分隔的对象名，自动创建包含文件的文件夹。想要在此文件夹中添加新文件时，只需要在上传文件至 COS 时，将 Key 填写为此目录前缀即可。
        dir_name = rec_user + '/'
        object_key = dir_name + f_path.split('/')[-1]
        self.client.upload_file(
            Bucket=self.bucket,  # Bucket 由 BucketName-APPID 组成
            Key=object_key,
            LocalFilePath=f_path,
            PartSize=10,
            MAXThread=10,
            progress_callback=self.upload_percentage,
        )

        async with aiofiles.open(os.path.join(self.rec_path, rec_user, "file_sizes.yml"), 'r') as p:
            file_details = yaml.safe_load(await p.read())
            await p.close()
        session_id = file_details["file_search"][f_path.split('/')[-1]]
        file_details["video_data"][session_id]["COSUploaded"] = True
        async with aiofiles.open(os.path.join(self.rec_path, rec_user, "file_sizes.yml"), 'w') as wp:
            await wp.write(yaml.dump(file_details, allow_unicode=True))
            await wp.close()
        return

    async def get_cos_uploaded_files(self, rec_user: str) -> list:
        response = self.client.list_objects(
            Bucket=self.bucket,
            Prefix=rec_user,
        )
        await asyncio.sleep(0.1)
        try:
            response = response["Contents"]
        except KeyError:
            return []
        uploaded_files = []
        for keys in response:
            uploaded_files.append(keys["Key"].split('/')[-1])
        return uploaded_files

    async def check_upload_list(self) -> list:
        response = self.client.list_multipart_uploads(
            Bucket=self.bucket,
        )
        await asyncio.sleep(0.1)
        try:
            response = response["Upload"]
        except KeyError:
            return []
        else:
            file_list = []
            for keys in response:
                file_list.append(keys["Key"].split('/')[-1])
            return file_list
