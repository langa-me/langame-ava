import asyncio
from typing import Iterable
import grpc
from ava import AvaStub, ava_pb2_grpc
from ava import ava_pb2

import unittest
import time
# For more channel options, please see https://grpc.io/grpc/core/group__grpc__arg__keys.html
CHANNEL_OPTIONS = [
    ("grpc.lb_policy_name", "pick_first"),
    ("grpc.enable_retries", 0),
    ("grpc.keepalive_timeout_ms", 10000),
]


async def run() -> None:
    def generate_messages() -> Iterable[ava_pb2.StreamAvaRequest]:
        messages = [
            ava_pb2.StreamAvaRequest(),
            ava_pb2.StreamAvaRequest(),
            ava_pb2.StreamAvaRequest(),
            ava_pb2.StreamAvaRequest(),
        ]
        for msg in messages:
            print("Sending")
            yield msg
    async with grpc.aio.insecure_channel(
        target="localhost:50051", options=CHANNEL_OPTIONS
    ) as channel:
        # gRPC AsyncIO bidi-streaming RPC API accepts both synchronous iterables
        # and async iterables.
        stub = ava_pb2_grpc.AvaStub(channel)
        call = stub.Stream(generate_messages())
        async for response in call:
            print(f"Received message")


class TestClient(unittest.TestCase):
    def test_client(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())
