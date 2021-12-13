from random import choices
from typing import Any, List, Tuple
from arrays import intersection
import openai
from enum import Enum
import os


class ProfanityTreshold(Enum):
    open = 1
    tolerant = 2
    strict = 3


class FinishReasonLengthException(Exception):
    pass


class ProfaneException(Exception):
    pass


def build_prompt(
    conversation_starter_examples: List[Any], topics: List[str], prompt_rows: int = 60,
) -> str:
    """
    Build a prompt for a GPT-like model based on a list of conversation starters.
    :param conversation_starter_examples: The list of conversation starters.
    :param topics: The list of topics.
    :param prompt_rows: The number of rows in the prompt.
    :return: prompt
    """
    random_conversation_starters = choices(conversation_starter_examples, k=500)
    found_conversation_starters = [
        f"{','.join(e[1]['topics'])} ### {e[1]['content']}"
        for e in random_conversation_starters
        if len(intersection(e[1]["topics"], topics)) > 0
    ]
    prompt = (
        (
            "\n".join(
                [
                    f"{','.join(e[1]['topics'])} ### {e[1]['content']}"
                    for e in random_conversation_starters
                ][0:prompt_rows]
            )
        )
        if not found_conversation_starters
        else "\n".join(found_conversation_starters[0:prompt_rows])
    )
    return prompt + "\n" + ",".join(topics) + " ###"


def openai_completion(prompt: str):
    response = openai.Completion.create(
        engine="davinci-codex",
        prompt=prompt,
        temperature=1,
        max_tokens=200,
        top_p=1,
        frequency_penalty=0.7,
        presence_penalty=0,
        stop=["\n"],
    )
    if (
        response["choices"][0]["finish_reason"] == "length"
        or not response["choices"][0]["text"]
    ):
        raise FinishReasonLengthException()
    return response["choices"][0]["text"]


def custom_completion(prompt: str):
    # TODO: eventually optional hf inference api
    from transformers import pipeline, set_seed, TextGenerationPipeline
    from random import randint

    generator: TextGenerationPipeline = pipeline(
        "text-generation",
        model="Langame/gpt2-starter",
        tokenizer="gpt2",
        use_auth_token=os.environ.get("HUGGINGFACE_TOKEN"),
    )
    set_seed(randint(0, 100))
    gen = generator(
        prompt,
        max_length=(len(prompt) / 5) + 100,
        num_return_sequences=1,
        return_text=False,
        return_full_text=False,
    )[0]
    completions = gen["generated_text"].split("\n")[0]
    return completions


def generate_conversation_starter(
    conversation_starter_examples: List[Any],
    topics: List[str],
    prompt_rows: int = 60,
    profanity_thresold: ProfanityTreshold = ProfanityTreshold.tolerant,
    no_openai: bool = False,
) -> str:
    """
    Build a prompt for the OpenAI API based on a list of conversation starters.
    :param conversation_starter_examples: The list of conversation starters.
    :param topics: The list of topics.
    :param prompt_rows: The number of rows in the prompt.
    :param check_profanity: Strictly above that threshold is considered profane and None is returned.
    :param no_openai: If True, the OpenAI API is not used, rather a local model.
    :return: conversation_starter
    """
    prompt = build_prompt(conversation_starter_examples, topics, prompt_rows,)
    text = custom_completion(prompt) if no_openai else openai_completion(prompt)
    conversation_starter = text.strip()

    if profanity_thresold.value > 1:
        # We check the whole output text,
        # in the future should probably check
        # topics and text in parallel and aggregate
        if is_profane(text) > (3 - profanity_thresold.value):
            raise ProfaneException()
    return conversation_starter


def is_profane(text: str, toxic_threshold: float = -0.355) -> int:
    """
    Check if text contains profanity.
    :param text: The text to check.
    :param toxic_threshold: This is the probability at which we evaluate that a "2" is likely real
    vs. should be discarded as a false positive
    :return: True if text contains profanity, False otherwise.
    """
    response = openai.Completion.create(
        engine="content-filter-alpha",
        prompt="<|endoftext|>" + text + "\n--\nLabel:",
        temperature=0,
        max_tokens=1,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        logprobs=10,
    )
    output_label = response["choices"][0]["text"]

    if output_label == "2":
        # If the model returns "2", return its confidence in 2 or other output-labels
        logprobs = response["choices"][0]["logprobs"]["top_logprobs"][0]

        # If the model is not sufficiently confident in "2",
        # choose the most probable of "0" or "1"
        # Guaranteed to have a confidence for 2 since this was the selected token.
        if logprobs["2"] < toxic_threshold:
            logprob_0 = logprobs.get("0", None)
            logprob_1 = logprobs.get("1", None)

            # If both "0" and "1" have probabilities, set the output label
            # to whichever is most probable
            if logprob_0 is not None and logprob_1 is not None:
                if logprob_0 >= logprob_1:
                    output_label = "0"
                else:
                    output_label = "1"
            # If only one of them is found, set output label to that one
            elif logprob_0 is not None:
                output_label = "0"
            elif logprob_1 is not None:
                output_label = "1"

            # If neither "0" or "1" are available, stick with "2"
            # by leaving output_label unchanged.

    # if the most probable token is none of "0", "1", or "2"
    # this should be set as unsafe
    if output_label not in ["0", "1", "2"]:
        output_label = "2"

    return int(output_label)
