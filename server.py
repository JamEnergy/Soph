import signal
import tornado
import tornado.websocket
import tornado.httpserver
import json
import asyncio
import inspect

class Server(tornado.websocket.WebSocketHandler):
    server = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def stop(self):
        Server.server.stop()

    def open(self, p):
        print("WebSocket opened")

    def on_message(self, message):
        try:
            print (message)
        except:
            pass
        j = json.loads(message)
        methodName = j["method"]
        args = j.get("args", ())
        kwargs = j.get("kwargs", {})
        res = self.path_args[0]

        method = getattr(self, methodName)
        if inspect.iscoroutinefunction(method):
            loop = asyncio.get_event_loop()
            task = loop.create_task(method(res, *args, **kwargs))

            def onFinish(r):
                ret = r.result()
                if type(ret) != str:
                    ret = json.dumps(ret)
                self.write_message(ret)

            task.add_done_callback( onFinish )
            future = asyncio.ensure_future(task)

        elif method:
            ret = method(res, *args, **kwargs)
            if type(ret) != str:
                ret = json.dumps(ret)
            self.write_message(ret)

        print("Returned")


    def on_close(self):
        print("WebSocket closed")

def run(port, cls, state):
    class Handler(cls, Server):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        pass

    class Stop(tornado.web.RequestHandler):
        loop = None
        server = None
        def get(self):
            print ("Stopping...")
            Stop.server.stop()
            Stop.loop.stop()

    class Ping(tornado.websocket.WebSocketHandler):
        def on_message(self, message):
            self.write_message("OK")

    application = tornado.web.Application([
        (r'/stop', Stop),
        (r'/ping', Ping),
        (r'/(.*)', Handler, {"state":state}),
    ])

    from tornado.platform.asyncio import AsyncIOMainLoop
    AsyncIOMainLoop().install()

    http_server = tornado.httpserver.HTTPServer(application)
    Server.server = http_server

    Stop.server = http_server
    Stop.loop = asyncio.get_event_loop()

    http_server.listen(port)

    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    application = tornado.web.Application([
        (r'/ws', Server),
    ])

    from tornado.platform.asyncio import AsyncIOMainLoop
    AsyncIOMainLoop().install()

    http_server = tornado.httpserver.HTTPServer(application)
    Server.server = http_server


    http_server.listen(8888)
    asyncio.get_event_loop().run_forever()