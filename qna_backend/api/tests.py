from rest_framework.test import APITestCase
from django.urls import reverse


class HealthTests(APITestCase):
    def test_health(self):
        url = reverse('Health')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"message": "Server is up!"})


class AuthAndChatTests(APITestCase):
    def setUp(self):
        self.signup_url = reverse('Signup')
        self.login_url = reverse('Login')
        self.conversations_url = reverse('Conversations')
        self.chat_url = reverse('Chat')

    def _auth_headers(self, access):
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}

    def test_signup_login_and_chat_mock(self):
        # Signup
        resp = self.client.post(self.signup_url, {"username": "alice", "email": "a@example.com", "password": "secret123"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["username"], "alice")

        # Login
        resp = self.client.post(self.login_url, {"username": "alice", "password": "secret123"}, format="json")
        self.assertEqual(resp.status_code, 200)
        access = resp.data["access"]
        self.assertTrue(access)

        # Create conversation
        resp = self.client.post(self.conversations_url, {"title": "Test"}, format="json", **self._auth_headers(access))
        self.assertEqual(resp.status_code, 201)
        conv_id = resp.data["id"]

        # Chat (will use mock if GEMINI_API_KEY not set)
        resp = self.client.post(self.chat_url, {"message": "Hello?", "conversation_id": conv_id}, format="json", **self._auth_headers(access))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("assistant", resp.data)
        self.assertEqual(resp.data["conversation_id"], conv_id)
