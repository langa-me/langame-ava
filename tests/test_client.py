import asyncio
from typing import List
import grpc
from ava import ConversationStarterRequest, ConversationStarterServiceStub
import unittest
# For more channel options, please see https://grpc.io/grpc/core/group__grpc__arg__keys.html
CHANNEL_OPTIONS = [
    ("grpc.lb_policy_name", "pick_first"),
    ("grpc.enable_retries", 0),
    ("grpc.keepalive_timeout_ms", 10000),
]


async def run(topics: List[str] = ["ice breaker"]) -> None:
    async with grpc.aio.insecure_channel(
        target="starter.langa.me/starter:443", options=CHANNEL_OPTIONS
    ) as channel:
        stub = ConversationStarterServiceStub(channel)
        request = ConversationStarterRequest()
        request.topics.extend(topics)
        response = await stub.GetConversationStarter(request)
        print(response)

class TestClient(unittest.TestCase):
    def test_client(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())

    def test_invalid_topic_should_throw(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(run(["foo"]))
        except grpc.RpcError as e:
            self.assertEqual(e.code(), grpc.StatusCode.INTERNAL)
