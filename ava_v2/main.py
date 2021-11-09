from concurrent import futures

import grpc
import ava.ava_pb2_grpc as ava_pb2_grpc


class BidirectionalService(ava_pb2_grpc.AvaServicer):

    def GetAva(self, request_iterator, context):
        for message in request_iterator:
            yield message


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ava_pb2_grpc.add_BidirectionalServicer_to_server(BidirectionalService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()