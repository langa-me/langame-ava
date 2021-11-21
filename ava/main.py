"""The graceful shutdown example for the asyncio Greeter server."""

# Native
import os
import sys
import json
import traceback
import asyncio
import logging
import grpc
sys.path.append(os.path.dirname(__file__))

# Google
from v1.api_pb2 import ConversationStarterRequest, ConversationStarterResponse, DESCRIPTOR
from v1.api_pb2_grpc import ConversationStarterServiceServicer, add_ConversationStarterServiceServicer_to_server
from grpc_reflection.v1alpha import reflection
from grpc_status import rpc_status
from google.rpc import status_pb2, code_pb2, error_details_pb2
from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore_v1.base_client import BaseClient
from google.cloud.firestore_v1.base_collection import BaseCollectionReference
from google.protobuf import any_pb2

# AI
import openai
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Own libs
from arrays import get_prompt
from strings import string_similarity

# Coroutines to be invoked when the event loop is shutting down.
_cleanup_coroutines = []


def build_raise_error(
    message: str,
    code: code_pb2,
    detail_message: str,
    context: grpc.aio.ServicerContext,
):
    detail = any_pb2.Any()
    detail.Pack(
        error_details_pb2.DebugInfo(
            stack_entries=traceback.format_stack(),
            detail=detail_message,
        )
    )
    rich_status = status_pb2.Status(
        code=code,
        message=message,
        details=[detail]
    )
    context.abort_with_status(rpc_status.to_status(rich_status))

class Ava(ConversationStarterServiceServicer):
    async def GetConversationStarter(
        self,
        request: ConversationStarterRequest,
        context: grpc.aio.ServicerContext,
    ) -> ConversationStarterResponse:
            if request is None or not request.topics:
                return build_raise_error("No topics in request", code_pb2.INVALID_ARGUMENT, "No topics in request", context)
            topics = request.topics

            for _ in range(5):
                samples = get_prompt(memes, topics)
                p = "\n".join([json.dumps(e) for e in samples[0:60]])
                try:
                    response = openai.Completion.create(
                        engine="davinci-codex",
                        prompt=p + "\n",
                        temperature=1,
                        max_tokens=100,
                        top_p=1,
                        frequency_penalty=0.7,
                        presence_penalty=0,
                        stop=["\n"],
                    )
                except Exception as e:
                    print(e)
                    continue
                if response["choices"][0]["finish_reason"] == "length":
                    continue
                text = response["choices"][0]["text"]
                try:
                    text = json.loads(text)
                    input_text = "fix: { " + text["content"] + " } </s>"
                except:
                    continue
                input_ids = tokenizer.encode(
                    input_text,
                    return_tensors="pt",
                    max_length=256,
                    truncation=True,
                    add_special_tokens=True,
                ).to(device)

                outputs = model.generate(
                    input_ids=input_ids,
                    max_length=256,
                    num_beams=4,
                    repetition_penalty=1.0,
                    length_penalty=1.0,
                    early_stopping=True,
                )

                sentence = tokenizer.decode(
                    outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True
                )

                if len(sentence) < 20 or string_similarity(text["content"], sentence) < 0.5:
                    continue
                res = ConversationStarterResponse()
                res.conversation_starter = sentence
                res.topics.extend(text["topics"] if "topics" in text else topics)
                return res
            return build_raise_error("No suitable response found", code_pb2.INTERNAL, "No suitable response found", context)


async def serve() -> None:
    server = grpc.aio.server()
    add_ConversationStarterServiceServicer_to_server(Ava(), server)
    SERVICE_NAMES = (
        DESCRIPTOR.services_by_name['ConversationStarterService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    PORT = os.environ["PORT"]
    assert PORT, "PORT environment variable must be set"
    listen_addr = f"[::]:{PORT}"
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

    openai.api_key = os.environ.get("OPENAI_KEY")
    openai.organization = os.environ.get("OPENAI_ORG")

    assert openai.api_key, "OPENAI_KEY not set"
    assert openai.organization, "OPENAI_ORG not set"

    model_name = "flexudy/t5-small-wav2vec2-grammar-fixer"
    device = "cpu"

    tokenizer = T5Tokenizer.from_pretrained(model_name)

    model = T5ForConditionalGeneration.from_pretrained(model_name).to(device)
    cred = credentials.Certificate("/etc/secrets/primary/svc.json")
    firebase_admin.initialize_app(cred)
    firestore_client: BaseClient = firestore.client()
    memes_ref: BaseCollectionReference = firestore_client.collection("memes")
    memes = []
    for e in firestore_client.collection("memes").stream():
        memes.append((e.id, e.to_dict()))

    assert memes, "No memes in database"

    logging.info(f"Fetched {len(memes)} memes")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(serve())
    finally:
        # loop.run_until_complete(*_cleanup_coroutines)
        loop.close()
