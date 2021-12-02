from quart import Quart, request, Response
import aiofiles
import yaml
import os

WAIT_STATUS_MINUTES = 1
app = Quart(__name__)


async def update_recording(resp_json):
    if resp_json["EventType"] not in ["SessionStarted", "SessionEnded"]:
        # FileOpening, FileClosed
        raw_name = str(resp_json["EventData"]["RelativePath"]).split("/")
        rec_path = os.path.join("/", "home", "pi", "record", raw_name[0])
        f_name = raw_name[1]
        try:
            async with aiofiles.open(os.path.join(rec_path, 'file_sizes.yml'), 'r', encoding='utf-8') as s:
                file_sizes = yaml.safe_load(await s.read())
                await s.close()
        except:
            file_sizes = {"ignore_cutting": False, "video_data": {
                resp_json["EventData"]["SessionId"]: {"LastEventTimestamp": resp_json["EventTimestamp"],
                                                      "FileClosed": False, "QQUploaded": False, "COSUploaded": False}},
                          "file_search": {f_name: resp_json["EventData"]["SessionId"]}}
        if file_sizes is None:
            file_sizes = {"ignore_cutting": False, "video_data": {
                resp_json["EventData"]["SessionId"]: {"LastEventTimestamp": resp_json["EventTimestamp"],
                                                      "FileClosed": False, "QQUploaded": False, "COSUploaded": False}},
                          "file_search": {f_name: resp_json["EventData"]["SessionId"]}}

        file_sizes["file_search"][f_name] = resp_json["EventData"]["SessionId"]

        if resp_json["EventType"] == "FileClosed":
            file_sizes["video_data"][resp_json["EventData"]["SessionId"]]["FileClosed"] = True
            file_sizes["video_data"][resp_json["EventData"]["SessionId"]]["LastEventTimestamp"] = resp_json[
                "EventTimestamp"]
        else:
            # FileOpening
            file_sizes["video_data"][resp_json["EventData"]["SessionId"]] = {
                "LastEventTimestamp": resp_json["EventTimestamp"],
                "FileClosed": False, "QQUploaded": False, "COSUploaded": False}

        async with aiofiles.open(os.path.join(rec_path, 'file_sizes.yml'), 'w', encoding='utf-8') as v:
            await v.write(yaml.dump(file_sizes, allow_unicode=True))
            await v.close()
        return
    return


@app.route('/', methods=['POST'])
async def respond_process():
    resp = await request.json
    print(resp)
    await update_recording(resp)
    return Response(response="", status=200)


if __name__ == '__main__':
    app.run(port=2233)
