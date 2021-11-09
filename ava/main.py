"""The graceful shutdown example for the asyncio Greeter server."""

import asyncio
import logging
import threading
from typing import Iterable
import time
import grpc
import ava_pb2
import ava_pb2_grpc
from google.protobuf.json_format import MessageToJson
from grpc_reflection.v1alpha import reflection

# Coroutines to be invoked when the event loop is shutting down.
_cleanup_coroutines = []


class Ava(ava_pb2_grpc.AvaServicer):
    async def Stream(
        self,
        request_iterator: Iterable[ava_pb2.StreamAvaRequest],
        context: grpc.aio.ServicerContext,
    ) -> Iterable[ava_pb2.StreamAvaResponse]:
        start_time = time.time()
        async for e in request_iterator:
            print(start_time, e)
            time.sleep(1)
            # yield ava_pb2.StreamAvaResponse()
        elapsed_time = time.time() - start_time
        return ava_pb2.StreamAvaResponse()


async def serve() -> None:
    server = grpc.aio.server()
    ava_pb2_grpc.add_AvaServicer_to_server(Ava(), server)
    SERVICE_NAMES = (
        ava_pb2.DESCRIPTOR.services_by_name['Ava'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()

    async def server_graceful_shutdown():
        logging.info("Starting graceful shutdown...")
        # Shuts down the server with 0 seconds of grace period. During the
        # grace period, the server won't accept new connections and allow
        # existing RPCs to continue within the grace period.
        await server.stop(5)

    _cleanup_coroutines.append(server_graceful_shutdown())
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(serve())
    finally:
        # loop.run_until_complete(*_cleanup_coroutines)
        loop.close()
