import server
import index
import utils
import os
import inspect


class MyHandler:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    def make(sid):
        return index.Index(os.path.join("data", sid, "index"), start=False)

    state = utils.SophDefaultDict(make)
    server.run(8888, MyHandler, state)