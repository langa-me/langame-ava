# Native
import os
import logging
import threading
import signal
from typing import List

# Google
from v1.api_pb2 import (
    ConversationStarterRequest,
    ConversationStarterResponse,
)

from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore import Client, DocumentSnapshot
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


class Ava:
    def __init__(
        self,
        fix_grammar: bool = False,
        profanity_thresold=ProfanityTreshold.tolerant,
        no_openai: bool = False,
        service_account_key_path: str = "/etc/secrets/primary/svc.json",
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
        cred = credentials.Certificate(service_account_key_path)
        firebase_admin.initialize_app(cred)
        self.firestore_client: Client = firestore.client()
        self.memes = []
        for e in self.firestore_client.collection("memes").stream():
            self.memes.append((e.id, e.to_dict()))

        assert self.memes, "No memes in database"

        self.logger.info(
            f"Fetched {len(self.memes)} memes, "
            + f"fix grammar: {self.fix_grammar}, "
            + f"profanity thresold: {self.profanity_thresold}, "
            + f"no openai: {self.no_openai}"
        )
        self.stopped = False

    def run(self):
        self.logger.info("Starting server")
        # Create an Event for notifying main thread.
        self.callback_done = threading.Event()
        doc_ref = self.firestore_client.collection("tests").where(
            "state", "==", "to-process"
        )
        self.doc_watch = doc_ref.on_snapshot(self.on_snapshot)
        while not self.stopped:
            pass

    def shutdown(self, signal, frame):
        self.stopped = True
        # self.doc_watch()
        self.firestore_client.close()
        self.callback_done.set()
        self.logger.info("Shutting down")

    def on_snapshot(self, doc_snapshot: List[DocumentSnapshot], changes, read_time):
        batch = self.firestore_client.batch()
        for doc in doc_snapshot:
            self.logger.info(f"Received document snapshot: {doc.id}, {doc.to_dict()}")
            if not doc.exists or doc.to_dict().get("topics", None) is None:
                self.logger.info(f"Document {doc.id} does not exist or has no topics")
                batch.update(
                    doc.reference, {"state": "error", "user_message": "no-topics"}
                )
                batch.commit()
                continue
            batch.update(doc.reference, {"state": "processing"})
            batch.commit()
            try:
                conversation_starter = self.generate(doc.get("topics"))
            except ProfaneException as e:
                self.logger.error(f"Profane: {e}")
                batch.update(
                    doc.reference, {"state": "error", "user_message": "profane"}
                )
                continue
            except Exception as e:
                self.logger.error(f"Error: {e}")
                batch.update(doc.reference, {"state": "error", "user_message": str(e)})
                continue
            batch.update(
                doc.reference,
                {"state": "processed", "conversation_starter": conversation_starter,},
            )
        batch.commit()
        self.callback_done.set()

    def generate(self, topics: List[str],) -> str:
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
            except FinishReasonLengthException as e:
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
            return conversation_starter
        raise Exception("not-found")


def serve(
    fix_grammar: bool = False,
    profanity_thresold: int = ProfanityTreshold.tolerant.value,
    no_openai: bool = False,
    service_account_key_path: str = "/etc/secrets/primary/svc.json",
) -> None:
    logger = logging.getLogger("ava")

    ava = Ava(
        fix_grammar,
        ProfanityTreshold(profanity_thresold),
        no_openai,
        service_account_key_path,
        logger,
    )

    # Setup signal handler
    signal.signal(signal.SIGINT, ava.shutdown)
    signal.signal(signal.SIGTERM, ava.shutdown)
    ava.run()


def main():
    logging.basicConfig(level=logging.INFO)

    openai.api_key = os.environ.get("OPENAI_KEY")
    openai.organization = os.environ.get("OPENAI_ORG")

    assert openai.api_key, "OPENAI_KEY not set"
    assert openai.organization, "OPENAI_ORG not set"
    # Check that HUGGINGFACE_TOKEN environment variable is set
    assert os.environ.get("HUGGINGFACE_TOKEN"), "HUGGINGFACE_TOKEN not set"

    fire.Fire(serve)


if __name__ == "__main__":
    main()
