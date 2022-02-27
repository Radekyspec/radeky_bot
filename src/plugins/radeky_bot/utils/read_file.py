import aiofiles
import yaml


async def read(path):
    async with aiofiles.open(path, "r") as r:
        content = await r.read()
        await r.close()
    return content


async def read_from_yaml(path):
    async with aiofiles.open(path, "r", encoding="utf-8") as ry:
        content = yaml.safe_load(await ry.read())
        await ry.close()
    return content
