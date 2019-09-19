import server
import utils
import os
import inspect
import textEngine
import json
from sophLogger import SophLogger
import aiohttp
import aiohttp.web

LOGGER = SophLogger("indexBundle.log")
class MyHandler:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        LOGGER("Listening now!")

    def initialize(self, **kwargs):
        self.indexes = kwargs.get("state", {})

    async def call(self, sid, name, *args, **kwargs):
        idx = self.indexes[sid]
        method = getattr(idx, name)
        if method:
            if inspect.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)

    def poo(self, text):
        return text

async def ping(request:aiohttp.web.Request):
    return aiohttp.web.Response(text="OK", status=200)


async def call(request:aiohttp.web.Request):
    state = request.app["state"]
    payload = await request.json()
    LOGGER("call: payload={0}".format(json.dumps(payload)))
    methodName = payload["method"]
    sid = payload["sid"]
    args = payload.get("args", ())
    kwargs = payload.get("kwargs", {})

    idx = state[sid]
    method = getattr(idx, methodName)
    if method:
        if inspect.iscoroutinefunction(method):
            ret = await method(*args, **kwargs)
        else:
            ret = method(*args, **kwargs)
        return aiohttp.web.Response(text=json.dumps(ret), status=200, content_type="application/json")
    return aiohttp.web.Response(text=":(", status=500)

if __name__ == "__main__":
    with open("options.json", "r", encoding="utf-8") as f:
        global_opts = json.loads(f.read(), encoding="utf-8")
    
    def make(key):
        opts = { "dir": os.path.join("data", str(key), "index"), 
                "startIndexing":global_opts.get("startIndexing", False) }
        return textEngine.TextEngine(opts)

    state = utils.SophDefaultDict(make)

    app = aiohttp.web.Application()
    app["state"] = state
    #app.router. add_routes([aiohttp.web.get('/call', call)])
    app.router.add_post("/call", call)
    app.router.add_get("/ping", ping)
    aiohttp.web.run_app(app, port=8888)
    #server.run(8888, MyHandler, state)