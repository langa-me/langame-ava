from ava.logic import (
    ProfanityTreshold,
    generate_conversation_starter,
    is_profane,
    is_profane,
)
from firebase_admin import credentials, firestore
import firebase_admin
import unittest
import openai
import os


class TestLogic(unittest.TestCase):
    def test_generate_conversation_starter(self):
        openai.api_key = os.environ["OPENAI_KEY"]
        openai.organization = os.environ["OPENAI_ORG"]
        cred = credentials.Certificate("./svc.dev.json")
        firebase_admin.initialize_app(cred)
        firestore_client = firestore.client()
        memes = [
            (e.id, e.to_dict()) for e in firestore_client.collection("memes").stream()
        ]
        new_topics, conversation_starter = generate_conversation_starter(
            memes, ["philosophy"]
        )
        print(new_topics, conversation_starter)

    def test_is_profane(self):
        openai.api_key = os.environ["OPENAI_KEY"]
        openai.organization = os.environ["OPENAI_ORG"]
        profane = is_profane("What is the fucking purpose of life")
        self.assertEqual(profane, 2)
        profane = is_profane(
            "god ### Do you believe in Santa? Why then do you believe in God?"
        )
        self.assertEqual(profane, 1)
        # Now a political conversation starter
        profane = is_profane("politic ### What do you think of China politic?")
        self.assertEqual(profane, 1)

    def test_generate_conversation_starter_profane(self):
        openai.api_key = os.environ["OPENAI_KEY"]
        openai.organization = os.environ["OPENAI_ORG"]
        cred = credentials.Certificate("./svc.dev.json")
        firebase_admin.initialize_app(cred)
        firestore_client = firestore.client()
        memes = [
            (e.id, e.to_dict()) for e in firestore_client.collection("memes").stream()
        ]
        new_topics, conversation_starter = generate_conversation_starter(
            memes, ["god"], profanity_thresold=ProfanityTreshold.strict
        )
        # Non deterministic tests, don't run in CI?
        self.assertEqual(new_topics, None)
        self.assertEqual(conversation_starter, None)
        new_topics, conversation_starter = generate_conversation_starter(
            memes, ["god"], profanity_thresold=ProfanityTreshold.tolerant
        )
        assert new_topics is not None
        assert conversation_starter is not None
        new_topics, conversation_starter = generate_conversation_starter(
            memes, ["god"], profanity_thresold=ProfanityTreshold.open
        )
        assert new_topics is not None
        assert conversation_starter is not None
