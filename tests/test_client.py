from __future__ import print_function

import grpc
import ava.ava_pb2_grpc as ava_pb2_grpc
import ava.ava_pb2 as ava_pb2

import unittest

class TestClient(unittest.TestCase):
    def test_client(self):
        def make_message(message):
            return ava_pb2.AvaRequest(
                message=message
            )
        def generate_messages():
            messages = [
                make_message("First message"),
                make_message("Second message"),
                make_message("Third message"),
                make_message("Fourth message"),
                make_message("Fifth message"),
            ]
            for msg in messages:
                print("Hello Server Sending you the %s" % msg.message)
                yield msg
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = ava_pb2_grpc.AvaStub(channel)
            responses = stub.Call(generate_messages())

        for response in responses:
            print("Hello from the server received your %s" % response.message)