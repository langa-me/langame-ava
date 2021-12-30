from firebase_admin import credentials
import firebase_admin
import unittest

class TestIntregation(unittest.TestCase):
    def setUp(self) -> None:
        cred = credentials.Certificate("./svc.dev.json")
        firebase_admin.initialize_app(cred)
        return super().setUp()

    def test_generate_conversation_starter(self):
        raise NotImplementedError
