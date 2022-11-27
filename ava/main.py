# Native
import asyncio
import os
import logging
import threading
import signal
from typing import List, Optional
from random import choice
import time
import traceback

# Google
from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore import Client, DocumentSnapshot, ArrayUnion
import fire

# AI
import openai
# from transformers import (
#     T5ForConditionalGeneration,
#     T5Tokenizer,
#     AutoTokenizer,
#     GPT2LMHeadModel,
# )
import torch
# from sentry_sdk import capture_exception

# Own libs
from langame.profanity import ProfanityThreshold
from langame.completion import (
    CompletionType,
    is_base_openai_model,
    is_base_gooseai_model,
    is_fine_tuned_openai,
    get_last_model,
)
from langame.conversation_starters import (
    get_existing_conversation_starters,
    generate_conversation_starter,
)
from langame.prompts import (
    extract_topics_from_personas
)
# from langame.functions.errors import (
#     init_errors
# )



class Ava:
    def __init__(
        self,
        service_account_key_path: str = "/etc/secrets/primary/svc.json",
        logger: logging.Logger = None,
        use_gpu: bool = False,
        shard: int = 0,
        only_sample_confirmed_conversation_starters: bool = True,
    ):
        self.logger = logger
        self.logger.info("initializing...")
        self.device = "cuda:0" if use_gpu and torch.cuda.is_available() else "cpu"
        self.completion_model = None
        self.completion_tokenizer = None
        self.shard = shard
        self.only_sample_confirmed_conversation_starters = (
            only_sample_confirmed_conversation_starters
        )
        self.default_api_completion_model = get_last_model()
        self.default_api_classification_model = get_last_model(is_classification=True)

        # Load the model and tokenizer for local generation
        # model_name_or_path = "Langame/distilgpt2-starter"
        # token = os.environ.get("HUGGINGFACE_TOKEN")
        # self.completion_model = GPT2LMHeadModel.from_pretrained(
        #     model_name_or_path, use_auth_token=token
        # ).to(self.device)
        # self.completion_model.eval().to(self.device)
        # self.completion_tokenizer = AutoTokenizer.from_pretrained(
        #     model_name_or_path, use_auth_token=token
        # )
        cred = credentials.Certificate(service_account_key_path)
        app = firebase_admin.initialize_app(cred)
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
        # init_errors(
        #     env="production" if app.project_id and not "dev" in app.project_id else "development"
        # )

        assert self.conversation_starters, "No conversation starters found"

        self.logger.info(
            f"Fetched {len(self.conversation_starters)} conversation starters, "
            + f"device: {self.device}, "
            + f"shard: {self.shard}, "
            + f"only_sample_confirmed_conversation_starters: {self.only_sample_confirmed_conversation_starters}, "
            + f"default_api_classification_model: {self.default_api_classification_model}"
        )
        self.stopped = False

    def run(self):
        """
        Run in a loop.
        """
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
            self.logger.info("Polling for new OpenAI model")
            last_model = get_last_model()
            if last_model["fine_tuned_model"] and last_model["fine_tuned_model"] != self.default_api_completion_model:
                self.default_api_completion_model = last_model["fine_tuned_model"]
                self.logger.info(
                    f"Updated default_api_completion_model to {self.default_api_completion_model}"
                )
            last_classification_model = get_last_model(is_classification=True)
            if last_classification_model["fine_tuned_model"] and last_classification_model["fine_tuned_model"] != self.default_api_classification_model:
                self.default_api_classification_model = last_classification_model["fine_tuned_model"]
                self.logger.info(
                    f"Updated default_api_classification_model to {self.default_api_classification_model}"
                )
            time.sleep(60)

    def shutdown(self, _, __):
        """
        Stop the ava service.
        """
        self.stopped = True
        self.firestore_client.close()
        self.callback_done.set()
        self.logger.info("Shutting down")

    def on_snapshot(self, doc_snapshot: List[DocumentSnapshot], changes, read_time):
        """
        Handle the new conversation starter request.
        :param doc_snapshot:
        :param changes:
        :param read_time:
        """
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
            completion_type = CompletionType[
                data_dict.get("completionType", "openai_api")
            ]
            profanity_threshold = ProfanityThreshold[
                data_dict.get("profanityThreshold", "open")
            ]
            api_completion_model = data_dict.get(
                "apiCompletionModel", self.default_api_completion_model
            )
            api_classification_model = data_dict.get(
                "apiClassificationModel", self.default_api_classification_model
            )
            topics = data_dict.get("topics", [])
            personas = data_dict.get(
                "personas", []
            )
            # if personas are provided, extract topics from it
            if len(personas) > 0:
                topics = loop.run_until_complete(
                    extract_topics_from_personas(personas)
                )
            # TODO: alternative idea: semantic search dataset with the personas
            # TODO: and then do few-shots inference with the selected samples
            if len(topics) == 0:
                topics = ["ice breaker"]
            new_doc_properties = {
                "disabled": True,
                "confirmed": False,
                "fixGrammar": fix_grammar,
                "parallelCompletions": parallel_completions,
                "completionType": completion_type.value,
                "profanityThreshold": profanity_threshold.value,
                "apiCompletionModel": api_completion_model,
                "apiClassificationModel": api_classification_model,
                "personas": personas,
                "topics": topics,
            }
            try:
                start_time = time.time()
                conversation_starters = self.generate(
                    topics=topics,
                    fix_grammar=fix_grammar,
                    parallel_completions=parallel_completions,
                    completion_type=completion_type,
                    profanity_threshold=profanity_threshold,
                    api_completion_model=api_completion_model,
                    api_classification_model=api_classification_model,
                )
                end_time = time.time()
                self.logger.info(
                    f"Generated {len(conversation_starters)} conversation starters"
                    + f" in {end_time - start_time} seconds"
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
                self.logger.error(e, traceback.format_exc())
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
                # capture_exception(e)
                continue
            # get the conversation starter with highest classification score
            # or random if no classification or all are 0
            conversation_starter = max(
                conversation_starters,
                key=lambda x: int(x.get("classification", 0)),
                default=choice(conversation_starters),
            )
            self.logger.info(f"Selected conversation starter: {conversation_starter}")
            obj = {
                **new_doc_properties,
                "state": "processed",
                "conversationStarters": conversation_starters,
                "content": conversation_starter["conversation_starter"],
                "brokenGrammar": conversation_starter.get("broken_grammar", ""),
            }
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
        completion_type: CompletionType = CompletionType.openai_api,
        profanity_threshold: ProfanityThreshold = ProfanityThreshold.open,
        api_completion_model: str = "curie:ft-personal-2022-02-09-05-17-08",
        api_classification_model: str = "ada:ft-personal-2022-05-01-04-04-50",
    ) -> List[dict]:
        """
        Generate conversation starters for a given topic.
        :param topics: list of topics
        :param fix_grammar: whether to fix grammar
        :param parallel_completions: number of parallel completions
        :param completion_type: completion type
        :param profanity_threshold: profanity threshold
        :param api_completion_model: api completion model
        :param api_classification_model: api classification model
        :return: list of conversation starters
        """
        prompt_rows = 5

        if (
            completion_type is CompletionType.openai_api
            # We only use 60 rows for davinci-codex and gooseai models
            and (
                is_base_openai_model(api_completion_model)
                or is_base_gooseai_model(api_completion_model)
            )
        ):
            prompt_rows = 60
        elif (
            completion_type is CompletionType.openai_api
            # Fine tuned OpenAI model use zero shot
            and is_fine_tuned_openai(api_completion_model)
        ):
            prompt_rows = 1

        self.logger.info(
            f"Generating conversation starter for {topics}"
            + f" completion_type {completion_type}"
            + f" profanity_threshold {profanity_threshold}"
            + f" fix_grammar {fix_grammar}"
            + f" parallel_completions {parallel_completions}"
            + f" api_completion_model {api_completion_model}"
            + f" api_classification_model {api_classification_model}"
            + f" prompt_rows {prompt_rows}"
        )
        return generate_conversation_starter(
            index=self.index,
            conversation_starter_examples=self.conversation_starters,
            topics=topics,
            profanity_threshold=profanity_threshold,
            completion_type=completion_type,
            prompt_rows=prompt_rows,
            model=None, #self.completion_model,
            tokenizer=None, #self.completion_tokenizer,
            logger=self.logger,
            sentence_embeddings_model=self.sentence_embeddings_model,
            fix_grammar=fix_grammar,
            grammar_tokenizer=None, #self.grammar_tokenizer,
            grammar_model=None, #self.grammar_model,
            use_classification=parallel_completions > 1,
            parallel_completions=parallel_completions,
            api_completion_model=api_completion_model,
            api_classification_model=api_classification_model,
        )


def serve(
    service_account_key_path: str = "/etc/secrets/primary/svc.json",
    use_gpu: bool = False,
    shard: int = 0,
    only_sample_confirmed_conversation_starters: bool = True,
) -> None:
    """
    Start the conversation starter generation service.
    :param service_account_key_path: path to service account key
    :param use_gpu: whether to use gpu
    :param shard: shard number
    :param only_sample_confirmed_conversation_starters:
    whether to only sample confirmed conversation starters
    """
    logger = logging.getLogger("ava")

    ava = Ava(
        service_account_key_path=service_account_key_path,
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
    """
    Starts ava.
    """
    logging.basicConfig(level=logging.INFO)

    openai.api_key = os.environ.get("OPENAI_KEY")
    openai.organization = os.environ.get("OPENAI_ORG")
    openai.log = "info"

    assert openai.api_key, "OPENAI_KEY not set"
    assert openai.organization, "OPENAI_ORG not set"
    assert os.environ.get("HUGGINGFACE_TOKEN"), "HUGGINGFACE_TOKEN not set"
    assert os.environ.get("HUGGINGFACE_KEY"), "HUGGINGFACE_KEY not set"

    fire.Fire(serve)


if __name__ == "__main__":
    main()
