#!/usr/bin/env python

import asyncio
import websockets
import json
from concurrent.futures import TimeoutError as ConnectionTimeoutError
import logging
logging.basicConfig(level=logging.INFO)
async def hello():
    # HOST = 'langame-ava-miqqfcvptq-uc.a.run.app'
    # HOST = '146.59.248.108:31236'
    HOST = '0.0.0.0:8080'
    # HOST = 'bot.langa.me'
    HTTPS = False
    # HTTPS = True
    timeout = 1200 
    try:
        URL = f'{"wss" if HTTPS else "ws"}://{HOST}/websocket'
        logging.info(f'Connecting to {URL}')
        connection = await asyncio.wait_for(websockets.connect(URL), timeout)
        await connection.send(json.dumps({'text': 'hello'}))
        while True:
            greeting = await connection.recv()
            print("< {}".format(greeting))
            msg = {"text": input(">> ")}
            print("sending", msg)
            await connection.send(json.dumps(msg))
            
    except ConnectionTimeoutError as e:
        print('Error connecting.', e)

asyncio.get_event_loop().run_until_complete(hello())

