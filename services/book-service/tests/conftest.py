"""
pytest configuration for book-service tests.

Adds the service root (services/book-service/) to sys.path so that
tests can import directly as `from app.X import Y` without depending
on the hyphenated folder name being importable as a Python module.
"""
import sys
import os

# Insert the book-service root so `from app.X` works
SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVICE_ROOT not in sys.path:
    sys.path.insert(0, SERVICE_ROOT)
