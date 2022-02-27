import aiofiles
import yaml


async def write(path, content):
    async with aiofiles.open(path, "w") as w:
        await w.write(content)
        await w.close()
    return


async def write_from_yaml(path, content):
    async with aiofiles.open(path, "w") as wy:
        await wy.write(yaml.dump(content, allow_unicode=True))
        await wy.close()
    return
