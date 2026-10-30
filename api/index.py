"""
Vercel Serverless Entrypoint for FastAPI
"""
import sys
import os

# Add root directory to sys.path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app

__all__ = ["app"]

