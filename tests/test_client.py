import asyncio
import grpc
from ava import ConversationStarterRequest, ConversationStarterServiceStub
import unittest
# For more channel options, please see https://grpc.io/grpc/core/group__grpc__arg__keys.html
CHANNEL_OPTIONS = [
    ("grpc.lb_policy_name", "pick_first"),
    ("grpc.enable_retries", 0),
    ("grpc.keepalive_timeout_ms", 10000),
]


async def run() -> None:
    async with grpc.aio.insecure_channel(
        target="localhost:8080", options=CHANNEL_OPTIONS
    ) as channel:
        stub = ConversationStarterServiceStub(channel)
        request = ConversationStarterRequest()
        request.topics.extend(["ice breaker"])
        response = await stub.GetConversationStarter(request)
        print(response)

class TestClient(unittest.TestCase):
    def test_client(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())
