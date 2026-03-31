import sys
import os
from fastapi import FastAPI

# Add parent directory to path to allow importing backend/app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app as backend_app

app = FastAPI()

# Mount the backend app at /api so rewrites work seamlessly
app.mount("/api", backend_app)
