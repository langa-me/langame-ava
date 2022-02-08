# Native
import asyncio
import os
import logging
import threading
import signal
from typing import List
from random import choice

# Google
from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore import Client, DocumentSnapshot, ArrayUnion
import fire

# AI
import openai
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    AutoTokenizer,
    GPT2LMHeadModel,
)
import torch


# Own libs
from langame.profanity import ProfanityThreshold
from langame.completion import (
    FinishReasonLengthException,
    CompletionType,
)
from langame.conversation_starters import (
    get_existing_conversation_starters,
    generate_conversation_starter,
)


class Ava:
    def __init__(
        self,
        profanity_threshold: ProfanityThreshold = ProfanityThreshold.tolerant,
        service_account_key_path: str = "/etc/secrets/primary/svc.json",
        completion_type: CompletionType = CompletionType.huggingface_api,
        tweet_on_generate: bool = False,
        logger: logging.Logger = None,
        use_gpu: bool = False,
        shard: int = 0,
        only_sample_confirmed_conversation_starters: bool = True,
    ):
        self.profanity_threshold = profanity_threshold
        self.completion_type = completion_type
        self.tweet_on_generate = tweet_on_generate
        self.logger = logger
        self.logger.info("initializing...")
        self.device = "cuda:0" if use_gpu and torch.cuda.is_available() else "cpu"
        self.completion_model = None
        self.completion_tokenizer = None
        self.shard = shard
        self.only_sample_confirmed_conversation_starters = (
            only_sample_confirmed_conversation_starters
        )
        model_name = "flexudy/t5-small-wav2vec2-grammar-fixer"
        self.grammar_tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.grammar_model = T5ForConditionalGeneration.from_pretrained(model_name).to(
            self.device
        )

        # if local completion, load the model and tokenizer
        if self.completion_type is CompletionType.local:
            model_name_or_path = "Langame/distilgpt2-starter"
            token = os.environ.get("HUGGINGFACE_TOKEN")
            self.completion_model = GPT2LMHeadModel.from_pretrained(
                model_name_or_path, use_auth_token=token
            ).to(self.device)
            self.completion_model.eval().to(self.device)
            self.completion_tokenizer = AutoTokenizer.from_pretrained(
                model_name_or_path, use_auth_token=token
            )
        cred = credentials.Certificate(service_account_key_path)
        firebase_admin.initialize_app(cred)
        self.firestore_client: Client = firestore.client()
        (
            self.conversation_starters,
            self.index,
            self.sentence_embeddings_model,
        ) = get_existing_conversation_starters(
            self.firestore_client,
            limit=None,
            logger=self.logger,
            confirmed=self.only_sample_confirmed_conversation_starters,
        )

        assert self.conversation_starters, "No conversation starters found"

        self.logger.info(
            f"Fetched {len(self.conversation_starters)} conversation starters, "
            + f"profanity threshold: {self.profanity_threshold}, "
            + f"completion type: {self.completion_type}, "
            + f"tweet on generate: {self.tweet_on_generate}, "
            + f"device: {self.device}, "
            + f"shard: {self.shard}, "
            + f"only_sample_confirmed_conversation_starters: {self.only_sample_confirmed_conversation_starters}, "
        )
        self.stopped = False

    def run(self):
        self.logger.info("Starting server")
        # Create an Event for notifying main thread.
        self.callback_done = threading.Event()
        doc_ref = (
            self.firestore_client.collection("memes").where("state", "==", "to-process")
            # shard is used in distributed scenarios
            .where("shard", "==", self.shard)
        )
        self.doc_watch = doc_ref.on_snapshot(self.on_snapshot)
        while not self.stopped:
            pass

    def shutdown(self, _, _2):
        self.stopped = True
        self.firestore_client.close()
        self.callback_done.set()
        self.logger.info("Shutting down")

    def on_snapshot(self, doc_snapshot: List[DocumentSnapshot], changes, read_time):
        batch = self.firestore_client.batch()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for doc in doc_snapshot:
            data_dict = doc.to_dict()
            self.logger.info(
                f"Received document snapshot: id: {doc.id},"
                + f" data: {data_dict}, changes: {changes}, read_time: {read_time}"
            )
            if not doc.exists or data_dict.get("topics", None) is None:
                self.logger.info(f"Document {doc.id} does not exist or has no topics")
                batch.set(
                    doc.reference,
                    {
                        "state": "error",
                        "disabled": True,
                        "error": "no-topics",
                        "confirmed": False,
                    },
                    merge=True,
                )
                batch.commit()
                continue
            if "content" in data_dict:
                self.logger.info(
                    "Document already have a conversation starter, skipping"
                )
                continue
            batch.set(doc.reference, {"state": "processing"}, merge=True)
            batch.commit()
            fix_grammar = data_dict.get("fixGrammar", False)
            parallel_completions = data_dict.get("parallelCompletions", 1)
            new_doc_properties = {
                "disabled": True,
                "confirmed": False,
                "fixGrammar": fix_grammar,
                "parallelCompletions": parallel_completions,
            }
            if fix_grammar:
                new_doc_properties["tags"] = ArrayUnion(["grammar"])
            try:
                conversation_starters = self.generate(
                    topics=data_dict.get("topics"),
                    fix_grammar=fix_grammar,
                    parallel_completions=parallel_completions,
                )
                # if all contains profane words
                if len(
                    [e for e in conversation_starters if e.get("profane", False)]
                ) == len(conversation_starters):
                    self.logger.warning(f"Profane: {conversation_starters}")
                    batch.set(
                        doc.reference,
                        {
                            **new_doc_properties,
                            "conversation_starters": conversation_starters,
                            "state": "error",
                            "error": "profane",
                        },
                        merge=True,
                    )
                    continue
            except Exception as e:
                self.logger.error(f"Error: {e}")
                error_code = (
                    # i.e. AI APIs rate limit exceeded
                    "resource-exhausted"
                    if "Rate limit" in str(e)
                    else "internal"
                )
                dev_message = (
                    "You have been rate limited, "
                    + "please reach out at contact@langa.me if you want an increase."
                    if "Rate limit" in str(e)
                    else str(e)
                )
                batch.set(
                    doc.reference,
                    {
                        **new_doc_properties,
                        "state": "error",
                        # if rate limited by openai, use "resource-exhausted" instead of internal
                        "error": error_code,
                        "developer_message": dev_message,
                    },
                    merge=True,
                )
                continue
            # get the conversation starter with highest classification score
            # or random if no classification or all are 0
            conversation_starter = max(
                conversation_starters,
                key=lambda x: int(x.get("classification", 0)),
                default=choice(conversation_starters),
            )
            self.logger.info(
                f"Selected conversation starter: {conversation_starter}"
            )
            obj = {
                **new_doc_properties,
                "state": "processed",
                "conversationStarters": conversation_starters,
                "content": conversation_starter["conversation_starter"],
                "brokenGrammar": conversation_starter.get("broken_grammar", ""),
                "tweet": self.tweet_on_generate,
            }
            if self.tweet_on_generate:
                obj["disabled"] = False
            batch.set(
                doc.reference, obj, merge=True,
            )
        batch.commit()
        self.callback_done.set()

    def generate(
        self,
        topics: List[str],
        fix_grammar: bool = False,
        parallel_completions: int = 1,
    ) -> List[dict]:
        conversation_starters = None
        for _ in range(5):
            try:
                self.logger.info(
                    f"Generating conversation starter for {topics}"
                    + f" using {self.completion_type} with profanity"
                    + f" threshold {self.profanity_threshold}"
                    + f" fix grammar {fix_grammar}"
                    + f" parallel completions {parallel_completions}"
                )
                conversation_starters = generate_conversation_starter(
                    index=self.index,
                    conversation_starter_examples=self.conversation_starters,
                    topics=topics,
                    profanity_threshold=self.profanity_threshold,
                    completion_type=self.completion_type,
                    prompt_rows=60
                    if self.completion_type is CompletionType.openai_api
                    else 5,
                    model=self.completion_model,
                    tokenizer=self.completion_tokenizer,
                    logger=self.logger,
                    sentence_embeddings_model=self.sentence_embeddings_model,
                    fix_grammar=fix_grammar,
                    grammar_tokenizer=self.grammar_tokenizer,
                    grammar_model=self.grammar_model,
                    use_classification=parallel_completions > 1,
                    parallel_completions=parallel_completions,
                )
            except FinishReasonLengthException as e:
                self.logger.error(e)
                continue

            return conversation_starters
        raise Exception("not-found")


def serve(
    profanity_threshold: str = "tolerant",
    service_account_key_path: str = "/etc/secrets/primary/svc.json",
    completion_type: str = "huggingface_api",
    tweet_on_generate: bool = False,
    use_gpu: bool = False,
    shard: int = 0,
    only_sample_confirmed_conversation_starters: bool = True,
) -> None:
    logger = logging.getLogger("ava")

    # Check that profanity_threshold is a ProfanityThreshold
    assert (
        profanity_threshold in ProfanityThreshold._member_names_
    ), f"profanity_threshold must be one of {ProfanityThreshold._member_names_}"
    # Check that completion_type is a CompletionType
    assert (
        completion_type in CompletionType._member_names_
    ), f"completion_type must be one of {CompletionType._member_names_}"

    ava = Ava(
        profanity_threshold=ProfanityThreshold[profanity_threshold],
        service_account_key_path=service_account_key_path,
        completion_type=CompletionType[completion_type],
        tweet_on_generate=tweet_on_generate,
        logger=logger,
        use_gpu=use_gpu,
        shard=shard,
        only_sample_confirmed_conversation_starters=only_sample_confirmed_conversation_starters,
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
    assert os.environ.get("HUGGINGFACE_TOKEN"), "HUGGINGFACE_TOKEN not set"
    assert os.environ.get("HUGGINGFACE_KEY"), "HUGGINGFACE_KEY not set"

    fire.Fire(serve)


if __name__ == "__main__":
    main()
