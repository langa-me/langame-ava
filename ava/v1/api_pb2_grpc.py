# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from ava.v1 import api_pb2 as ava_dot_v1_dot_api__pb2


class ConversationStarterServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.GetConversationStarter = channel.unary_unary(
                '/ava.ConversationStarterService/GetConversationStarter',
                request_serializer=ava_dot_v1_dot_api__pb2.ConversationStarterRequest.SerializeToString,
                response_deserializer=ava_dot_v1_dot_api__pb2.ConversationStarterResponse.FromString,
                )


class ConversationStarterServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def GetConversationStarter(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ConversationStarterServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'GetConversationStarter': grpc.unary_unary_rpc_method_handler(
                    servicer.GetConversationStarter,
                    request_deserializer=ava_dot_v1_dot_api__pb2.ConversationStarterRequest.FromString,
                    response_serializer=ava_dot_v1_dot_api__pb2.ConversationStarterResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'ava.ConversationStarterService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class ConversationStarterService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def GetConversationStarter(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ava.ConversationStarterService/GetConversationStarter',
            ava_dot_v1_dot_api__pb2.ConversationStarterRequest.SerializeToString,
            ava_dot_v1_dot_api__pb2.ConversationStarterResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)