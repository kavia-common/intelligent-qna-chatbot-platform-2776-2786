# intelligent-qna-chatbot-platform-2776-2786

Backend (Django/DRF) provides:
- Auth: POST /api/auth/signup/, POST /api/auth/login/ (JWT)
- Conversations: GET/POST /api/conversations/, GET/DELETE /api/conversations/{id}/
- Chat: POST /api/chat/ (message, optional conversation_id, optional system_prompt)
- Health: GET /api/health/
- API Docs: /docs

Environment setup:
- Copy qna_backend/.env.example to .env and fill in values (especially GEMINI_API_KEY).
- If GEMINI_API_KEY is not set, backend returns mocked AI responses. Set USE_MOCK_AI=true to force mock mode.
- Database defaults to SQLite (configurable via Django settings).

Run:
- pip install -r qna_backend/requirements.txt
- python qna_backend/manage.py migrate
- python qna_backend/manage.py runserver 0.0.0.0:8000

Notes:
- Chat uses LangChain with Google Gemini via `langchain-google-genai`. Provide GEMINI_API_KEY to enable real responses.
- JWT via `djangorestframework-simplejwt`. Include header: Authorization: Bearer <access_token>.
