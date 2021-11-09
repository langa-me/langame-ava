import os
import sys
# 😎 https://github.com/protocolbuffers/protobuf/issues/1491#issuecomment-429735834
sys.path.append(os.path.dirname(__file__))

from ava_pb2_grpc import AvaStub
import ava_pb2
