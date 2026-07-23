import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

for env_path in [
    os.path.join(os.getcwd(), '.env'),
    os.path.join(os.path.dirname(__file__), '..', '.env'),
]:
    if os.path.exists(env_path):
        from dotenv import load_dotenv
        load_dotenv(env_path)
        break

from .routes import router

app = FastAPI(title="NotePilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
