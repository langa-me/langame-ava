# Native
import os
import sys
import json
import asyncio
import logging
import grpc

sys.path.append(os.path.dirname(__file__))

# Google
from v1.api_pb2 import (
    ConversationStarterRequest,
    ConversationStarterResponse,
    DESCRIPTOR,
)
from v1.api_pb2_grpc import (
    ConversationStarterServiceServicer,
    add_ConversationStarterServiceServicer_to_server,
)
from grpc_reflection.v1alpha import reflection
from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore_v1.base_client import BaseClient
import fire

# AI
import openai
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Own libs
from logic import (
    FinishReasonLengthException,
    ProfaneException,
    ProfanityTreshold,
    generate_conversation_starter,
)
from strings import string_similarity

# Coroutines to be invoked when the event loop is shutting down.
_cleanup_coroutines = []


class Ava(ConversationStarterServiceServicer):
    def __init__(
        self,
        fix_grammar: bool = False,
        profanity_thresold=ProfanityTreshold.tolerant,
        no_openai: bool = False,
        logger: logging.Logger = None,
    ):
        self.fix_grammar = fix_grammar
        self.profanity_thresold = profanity_thresold
        self.no_openai = no_openai
        self.logger = logger
        if self.fix_grammar:
            model_name = "flexudy/t5-small-wav2vec2-grammar-fixer"
            self.device = "cpu"
            self.tokenizer = T5Tokenizer.from_pretrained(model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(model_name).to(
                self.device
            )
        cred = credentials.Certificate("/etc/secrets/primary/svc.json")
        firebase_admin.initialize_app(cred)
        firestore_client: BaseClient = firestore.client()
        self.memes = []
        for e in firestore_client.collection("memes").stream():
            self.memes.append((e.id, e.to_dict()))

        assert self.memes, "No memes in database"

        self.logger.info(
            f"Fetched {len(self.memes)} memes, "
            + f"fix grammar: {self.fix_grammar}, "
            + f"profanity thresold: {self.profanity_thresold}, "
            + f"no openai: {self.no_openai}"
        )

    async def GetConversationStarter(
        self, request: ConversationStarterRequest, context: grpc.aio.ServicerContext,
    ) -> ConversationStarterResponse:
        if request is None or not request.topics:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("no-topics")
            return ConversationStarterResponse()
        topics = request.topics
        conversation_starter = None
        for _ in range(5):
            try:
                # If fail many times, go for random topic
                conversation_starter = generate_conversation_starter(
                    self.memes,
                    topics,
                    profanity_thresold=self.profanity_thresold,
                    no_openai=self.no_openai,
                    prompt_rows=5 if self.no_openai else 60,
                )
            except ProfaneException as e:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("profane")
                return ConversationStarterResponse()
            except (FinishReasonLengthException, Exception) as e:
                self.logger.error(e)
                continue

            if self.fix_grammar:
                input_text = "fix: { " + conversation_starter + " } </s>"
                input_ids = self.tokenizer.encode(
                    input_text,
                    return_tensors="pt",
                    max_length=256,
                    truncation=True,
                    add_special_tokens=True,
                ).to(self.device)

                outputs = self.model.generate(
                    input_ids=input_ids,
                    max_length=256,
                    num_beams=4,
                    repetition_penalty=1.0,
                    length_penalty=1.0,
                    early_stopping=True,
                )

                sentence = self.tokenizer.decode(
                    outputs[0],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )

                if (
                    len(sentence) < 20
                    or string_similarity(conversation_starter, sentence) < 0.5
                ):
                    continue
                conversation_starter = sentence
            res = ConversationStarterResponse()
            res.conversation_starter = conversation_starter
            res.topics.extend(topics)
            return res
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details("not-found")
        return ConversationStarterResponse()


async def serve(
    fix_grammar: bool = False,
    profanity_thresold: int = ProfanityTreshold.tolerant.value,
    no_openai: bool = False,
) -> None:
    logger = logging.getLogger("ava")
    server = grpc.aio.server()

    add_ConversationStarterServiceServicer_to_server(
        Ava(fix_grammar, ProfanityTreshold(profanity_thresold), no_openai, logger,),
        server,
    )
    SERVICE_NAMES = (
        DESCRIPTOR.services_by_name["ConversationStarterService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    PORT = os.environ["PORT"]
    assert PORT, "PORT environment variable must be set"
    listen_addr = f"[::]:{PORT}"
    server.add_insecure_port(listen_addr)
    logger.info("Starting server on %s", listen_addr)
    await server.start()

    async def server_graceful_shutdown():
        logger.info("Starting graceful shutdown...")
        # Shuts down the server with 0 seconds of grace period. During the
        # grace period, the server won't accept new connections and allow
        # existing RPCs to continue within the grace period.
        await server.stop(5)

    _cleanup_coroutines.append(server_graceful_shutdown())
    await server.wait_for_termination()


def main():
    logging.basicConfig(level=logging.INFO)

    openai.api_key = os.environ.get("OPENAI_KEY")
    openai.organization = os.environ.get("OPENAI_ORG")

    assert openai.api_key, "OPENAI_KEY not set"
    assert openai.organization, "OPENAI_ORG not set"
    # Check that HUGGINGFACE_TOKEN environment variable is set
    assert os.environ.get("HUGGINGFACE_TOKEN"), "HUGGINGFACE_TOKEN not set"

    loop = asyncio.get_event_loop()
    try:
        fire.Fire(serve)
    finally:
        loop.run_until_complete(*_cleanup_coroutines)
        loop.close()


if __name__ == "__main__":
    main()
