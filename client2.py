#!/usr/bin/env python

import asyncio
import websockets
import json
from concurrent.futures import TimeoutError as ConnectionTimeoutError
async def hello():
    HOST = 'langame-ava-miqqfcvptq-uc.a.run.app'
    # timeout in seconds
    timeout = 1200 
    try:
    # make connection attempt
        connection = await asyncio.wait_for(websockets.connect(f'wss://{HOST}/websocket'), timeout)
        d = {
            "text": "hello"
        }

        await connection.send(json.dumps(d))

        greeting = await connection.recv()
        print("< {}".format(greeting))
                
                
        d = {
            "text": "begin"
        }

        await connection.send(json.dumps(d))

        greeting = await connection.recv()
        print("< {}".format(greeting))
    except ConnectionTimeoutError as e:
        # handle error
        print('Error connecting.')
    # async with websockets.connect(f'ws://${HOST}:8080/websocket') as websocket:

    #     d = {
    #         "text": "hello"
    #     }

    #     await websocket.send(json.dumps(d))

    #     greeting = await websocket.recv()
    #     print("< {}".format(greeting))

asyncio.get_event_loop().run_until_complete(hello())

