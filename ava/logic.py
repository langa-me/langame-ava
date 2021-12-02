from random import choices
from typing import Any, List, Tuple, Optional
from arrays import intersection
import openai

def generate_conversation_starter(
    conversation_starter_examples: List[Any], topics: List[str], prompt_rows: int = 60,
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Build a prompt for the OpenAI API based on a list of conversation starters.
    :param conversation_starter_examples: The list of conversation starters.
    :param topics: The list of topics.
    :return: topics, conversation_starter
    """
    random_conversation_starters = choices(conversation_starter_examples, k=500)
    found_conversation_starters = [
        f"{','.join(e[1]['topics'])} ### {e[1]['content']}"
        for e in random_conversation_starters
        if len(intersection(e[1]["topics"], topics)) > 0
    ]
    prompt = (
        ("\n".join(
            [
                f"{','.join(e[1]['topics'])} ### {e[1]['content']}"
                for e in random_conversation_starters
            ][0:prompt_rows]
        )
        + "\n"
        + ",".join(topics)
        + " ###")
        if not found_conversation_starters
        else "\n".join(found_conversation_starters[0:prompt_rows]) + "\n"
    )
    # TODO: content filter, classification etc
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
    if response["choices"][0]["finish_reason"] == "length" or not response["choices"][0]["text"]:
        return None, None
    text = response["choices"][0]["text"]
    new_topics = []
    if found_conversation_starters:
        splitted = text.split("###")
        new_topics = splitted[0].strip().split(",")
        conversation_starter = splitted[1].strip()
    else:
        new_topics = topics
        conversation_starter = text.strip()
    return new_topics, conversation_starter
