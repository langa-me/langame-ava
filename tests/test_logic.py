from ava.logic import generate_conversation_starter
from firebase_admin import credentials, firestore
import firebase_admin
import unittest
import openai
import os

class TestLogic(unittest.TestCase):
    def test_logic(self):
        openai.api_key = os.environ["OPENAI_KEY"]
        openai.organization = os.environ["OPENAI_ORG"]
        cred = credentials.Certificate("./svc.dev.json")
        firebase_admin.initialize_app(cred)
        firestore_client = firestore.client()
        memes = [(e.id, e.to_dict()) for e in firestore_client.collection("memes").stream()]
        new_topics, conversation_starter = generate_conversation_starter(memes, ["philosophy"])
        print(new_topics, conversation_starter)
