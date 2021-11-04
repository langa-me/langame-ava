#!/usr/bin/env python

import asyncio
import websockets
import json
from concurrent.futures import TimeoutError as ConnectionTimeoutError
import logging
import time
logging.basicConfig(level=logging.INFO)
async def hello():
    # HOST = 'langame-ava-miqqfcvptq-uc.a.run.app'
    # HOST = '146.59.248.108:31236'
    # HOST = 'localhost:8080'
    HOST = 'bot.langa.me'
    HTTPS = True
    timeout = 1200 
    try:
        URL = f'{"wss" if HTTPS else "ws"}://{HOST}/websocket'
        logging.info(f'Connecting to {URL}')
        connection = await asyncio.wait_for(websockets.connect(URL), timeout)
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
        time.sleep(100000)
    except ConnectionTimeoutError as e:
        print('Error connecting.', e)

asyncio.get_event_loop().run_until_complete(hello())

