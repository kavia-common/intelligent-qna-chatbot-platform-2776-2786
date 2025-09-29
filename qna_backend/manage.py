#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Attempt to load environment variables from a .env file, if present.
# This ensures GEMINI_API_KEY and other config are available in development/runtime
# when a process manager hasn't exported them.
try:
    from dotenv import load_dotenv  # type: ignore
    # Load .env from the project root (qna_backend/.env)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(current_dir, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
except Exception:
    # Do not fail if python-dotenv is not installed; app can still run if env is already set.
    pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
