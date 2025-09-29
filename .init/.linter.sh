#!/bin/bash
cd /home/kavia/workspace/code-generation/intelligent-qna-chatbot-platform-2776-2786/qna_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

