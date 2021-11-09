from concurrent import futures

import grpc
import ava.ava_pb2_grpc as ava_pb2_grpc
import logging

class Ava(ava_pb2_grpc.Ava):

    def GetAva(self, request_iterator, context):
        for message in request_iterator:
            yield message


def serve():
    logging.basicConfig(level=logging.INFO)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ava_pb2_grpc.add_AvaServicer_to_server(Ava(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logging.info('Ava server started')
    server.wait_for_termination()


if __name__ == '__main__':
    serve()