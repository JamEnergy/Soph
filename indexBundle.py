import server
import utils
import os
import inspect
import textEngine
import json

class MyHandler:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print ("Listening now!")

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

if __name__ == "__main__":
    with open("options.json", "r", encoding="utf-8") as f:
        global_opts = json.loads(f.read(), encoding = "utf-8")
    
    def make(key):
        opts = { "dir": os.path.join("data", str(key), "index"), 
                "startIndexing":global_opts.get("startIndexing", False) }
        return textEngine.TextEngine(opts)

    state = utils.SophDefaultDict(make)
    server.run(8888, MyHandler, state)