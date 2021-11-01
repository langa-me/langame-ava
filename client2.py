#!/usr/bin/env python

import asyncio
import websockets
import json

async def hello():
    async with websockets.connect('ws://localhost:8080/websocket') as websocket:

        d = {
            "text": "hello"
        }

        await websocket.send(json.dumps(d))

        greeting = await websocket.recv()
        print("< {}".format(greeting))

asyncio.get_event_loop().run_until_complete(hello())