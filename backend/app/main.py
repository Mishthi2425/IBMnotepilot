from dotenv import load_dotenv
import os

# Load .env FIRST before anything else
for env_path in [
    os.path.join(os.getcwd(), '.env'),
    os.path.join(os.path.dirname(__file__), '..', '.env'),
]:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"main.py: Loaded .env from {env_path}")
        break
else:
    print(f"main.py: .env not found")

print(f"main.py: LLM_API_KEY={'SET' if os.getenv('LLM_API_KEY') else 'NOT SET'}")
print(f"main.py: LLM_BASE_URL={os.getenv('LLM_BASE_URL', 'NOT SET')}")
print(f"main.py: LLM_MODEL={os.getenv('LLM_MODEL', 'NOT SET')}")

from . import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
