import asyncio
import websockets
import json

async def call(port = 8888, path = "196373421834240000", method = "", *args, **kwargs):
    url = 'ws://localhost:{0}/{1}'.format(port, path)
    async with websockets.connect(url) as websocket:
        payload = json.dumps( {"method":method, "args":args, "kwargs":kwargs })
        await websocket.send(payload)
        greeting = await websocket.recv()
        try:
            return json.loads(greeting)
        except:
            return greeting

if __name__ == "__main__":
    tasks = [call(8888, "196373421834240000", "call", "queryStats", "Vindictus") for i in range(0,1)]
    
    asyncio.get_event_loop().run_until_complete( asyncio.gather(*tasks))