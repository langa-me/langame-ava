import os
import sys
# 😎 https://github.com/protocolbuffers/protobuf/issues/1491#issuecomment-429735834
sys.path.append(os.path.dirname(__file__))

from v1.api_pb2_grpc import *
from v1.api_pb2 import *

from main import main
